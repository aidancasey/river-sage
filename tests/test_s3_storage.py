"""
Unit tests for S3 storage.

Uses moto to mock AWS S3 for testing without real AWS resources.
"""

import pytest
import json
import gzip
from datetime import datetime
from moto import mock_aws
import boto3

from src.storage.s3_storage import S3Storage
from src.config.settings import S3Config
from src.parsers.esb_hydro_parser import ParsedFlowData, FlowReading


@pytest.fixture
def s3_config():
    """Create S3 configuration for testing."""
    return S3Config(
        bucket_name="test-river-data",
        region="us-east-1",
        raw_prefix="raw",
        parsed_prefix="parsed",
        aggregated_prefix="aggregated"
    )


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        # Create bucket
        s3.create_bucket(Bucket='test-river-data')
        yield s3


@pytest.fixture
def storage(s3_config, mock_s3_client):
    """Create S3 storage instance with mock client."""
    return S3Storage(s3_config, s3_client=mock_s3_client)


@pytest.fixture
def sample_parsed_data():
    """Create sample parsed flow data."""
    current = FlowReading(
        timestamp=datetime(2025, 12, 5, 17, 0),
        flow_rate_m3s=127.0
    )
    historical = [
        FlowReading(datetime(2025, 12, 5, 16, 0), 126.0),
        FlowReading(datetime(2025, 12, 5, 15, 0), 125.0),
    ]
    return ParsedFlowData(
        station="Inniscarra",
        river="River Lee",
        current_reading=current,
        historical_readings=historical,
        parsed_at=datetime.utcnow(),
        source_hash="abc123"
    )


def test_storage_initialization(storage, s3_config):
    """Test S3Storage initialization."""
    assert storage.config == s3_config
    assert storage.s3 is not None


def test_check_bucket_exists(storage):
    """Test bucket existence check."""
    assert storage.check_bucket_exists() is True


def test_upload_raw_pdf(storage, sample_parsed_data):
    """Test uploading raw PDF."""
    pdf_content = b'%PDF-1.7 fake content'
    timestamp = sample_parsed_data.current_reading.timestamp

    s3_key = storage.upload_raw_pdf(
        content=pdf_content,
        station_id="inniscarra",
        timestamp=timestamp,
        content_hash="test123"
    )

    # Verify key format
    assert "raw/inniscarra" in s3_key
    assert "2025/12/05" in s3_key
    assert s3_key.endswith(".pdf")

    # Verify upload
    response = storage.s3.get_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )
    assert response['Body'].read() == pdf_content
    assert response['ContentType'] == 'application/pdf'


def test_upload_parsed_json(storage, sample_parsed_data):
    """Test uploading parsed JSON."""
    s3_key = storage.upload_parsed_json(
        parsed_data=sample_parsed_data,
        station_id="inniscarra",
        compress=True
    )

    # Verify key format
    assert "parsed/inniscarra" in s3_key
    assert "202512" in s3_key
    assert s3_key.endswith(".json.gz")

    # Verify upload and content
    response = storage.s3.get_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )

    # Decompress and parse
    compressed_content = response['Body'].read()
    json_content = gzip.decompress(compressed_content)
    data = json.loads(json_content)

    assert data['station'] == "Inniscarra"
    assert data['river'] == "River Lee"
    assert data['current_reading']['flow_rate_m3s'] == 127.0


def test_upload_parsed_json_uncompressed(storage, sample_parsed_data):
    """Test uploading parsed JSON without compression."""
    s3_key = storage.upload_parsed_json(
        parsed_data=sample_parsed_data,
        station_id="inniscarra",
        compress=False
    )

    # Verify key format
    assert s3_key.endswith(".json")
    assert ".gz" not in s3_key

    # Verify upload and content
    response = storage.s3.get_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )

    json_content = response['Body'].read()
    data = json.loads(json_content)

    assert data['station'] == "Inniscarra"


def test_update_latest_aggregated(storage, sample_parsed_data):
    """Test updating latest aggregated data."""
    s3_key = storage.update_latest_aggregated(
        parsed_data=sample_parsed_data,
        station_id="inniscarra"
    )

    # Verify key format
    assert s3_key == "aggregated/inniscarra_latest.json"

    # Verify content
    response = storage.s3.get_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )

    data = json.loads(response['Body'].read())

    assert data['station'] == "Inniscarra"
    assert data['river'] == "River Lee"
    assert data['latest_reading']['flow_rate_m3s'] == 127.0
    assert 'updated_at' in data
    assert 'statistics' in data


def test_get_latest_reading(storage, sample_parsed_data):
    """Test retrieving latest reading."""
    # First upload
    storage.update_latest_aggregated(
        parsed_data=sample_parsed_data,
        station_id="inniscarra"
    )

    # Then retrieve
    data = storage.get_latest_reading("inniscarra")

    assert data is not None
    assert data['station'] == "Inniscarra"
    assert data['latest_reading']['flow_rate_m3s'] == 127.0


def test_get_latest_reading_not_found(storage):
    """Test retrieving latest reading when none exists."""
    data = storage.get_latest_reading("nonexistent")
    assert data is None


def test_upload_daily_summary(storage):
    """Test uploading daily summary."""
    date = datetime(2025, 12, 5)
    summary = {
        "date": "2025-12-05",
        "min_flow": 63.0,
        "max_flow": 127.0,
        "mean_flow": 92.2,
        "readings_count": 30
    }

    s3_key = storage.upload_daily_summary(
        station_id="inniscarra",
        date=date,
        summary_data=summary
    )

    # Verify key format
    assert "aggregated/inniscarra_daily_20251205.json" == s3_key

    # Verify content
    response = storage.s3.get_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )

    data = json.loads(response['Body'].read())
    assert data['min_flow'] == 63.0
    assert data['max_flow'] == 127.0


def test_list_historical_files(storage, sample_parsed_data):
    """Test listing historical files."""
    # Upload a few files
    storage.upload_parsed_json(
        parsed_data=sample_parsed_data,
        station_id="inniscarra",
        compress=True
    )

    # List files
    files = storage.list_historical_files(
        station_id="inniscarra",
        prefix_type="parsed"
    )

    assert len(files) > 0
    assert all("parsed/inniscarra" in f for f in files)


def test_list_historical_files_empty(storage):
    """Test listing historical files when none exist."""
    files = storage.list_historical_files(
        station_id="nonexistent",
        prefix_type="parsed"
    )

    assert files == []


def test_s3_key_generation(s3_config):
    """Test S3 key path generation."""
    # Test raw key
    raw_key = s3_config.get_raw_key(
        station_id="inniscarra",
        timestamp="20251205_170000",
        filename="test.pdf"
    )
    assert raw_key == "raw/inniscarra/2025/12/05/test.pdf"

    # Test parsed key
    parsed_key = s3_config.get_parsed_key(
        station_id="inniscarra",
        year_month="202512"
    )
    assert parsed_key == "parsed/inniscarra/2025/12/inniscarra_flow_202512.json"

    # Test latest key
    latest_key = s3_config.get_latest_key("inniscarra")
    assert latest_key == "aggregated/inniscarra_latest.json"


def test_upload_with_metadata(storage, sample_parsed_data):
    """Test that uploads include proper metadata."""
    pdf_content = b'%PDF content'
    timestamp = sample_parsed_data.current_reading.timestamp

    s3_key = storage.upload_raw_pdf(
        content=pdf_content,
        station_id="inniscarra",
        timestamp=timestamp,
        content_hash="test123"
    )

    # Get object with metadata
    response = storage.s3.head_object(
        Bucket=storage.config.bucket_name,
        Key=s3_key
    )

    metadata = response['Metadata']
    assert 'station-id' in metadata
    assert metadata['station-id'] == "inniscarra"
    assert 'content-hash' in metadata


def test_storage_class_configuration(s3_config):
    """Test storage class configuration."""
    assert s3_config.storage_class == "STANDARD"

    # Test with different storage class
    config = S3Config(
        bucket_name="test",
        storage_class="INTELLIGENT_TIERING"
    )
    assert config.storage_class == "INTELLIGENT_TIERING"
