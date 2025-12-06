#!/bin/bash
# cleanup.sh - Remove redundant files from river-data-scraper project
#
# This script removes development test scripts and old deployment files
# that have been replaced by proper tests and AWS SAM deployment.

set -e

echo "🧹 River Data Scraper - Cleanup Script"
echo "======================================"
echo ""

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Count files before
BEFORE_COUNT=$(find . -maxdepth 1 -type f | wc -l)

echo -e "${BLUE}Files to be removed:${NC}"
echo "  • analyze_pdf.py (PDF exploration script)"
echo "  • test_connection.py (HTTP test - now in tests/)"
echo "  • test_end_to_end.py (E2E test - now in tests/)"
echo "  • test_end_to_end_with_s3.py (S3 E2E test - now in tests/)"
echo "  • test_parser.py (Parser test - now in tests/)"
echo "  • deploy.sh (Replaced by SAM)"
echo "  • setup.sh (Instructions in README.md)"
echo "  • .DS_Store files (macOS artifacts)"
echo ""

read -p "Continue with cleanup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Removing development test scripts...${NC}"

# Remove development test scripts
rm -f analyze_pdf.py && echo "  ✓ Removed analyze_pdf.py"
rm -f test_connection.py && echo "  ✓ Removed test_connection.py"
rm -f test_end_to_end.py && echo "  ✓ Removed test_end_to_end.py"
rm -f test_end_to_end_with_s3.py && echo "  ✓ Removed test_end_to_end_with_s3.py"
rm -f test_parser.py && echo "  ✓ Removed test_parser.py"

echo ""
echo -e "${YELLOW}Removing old deployment script...${NC}"
rm -f deploy.sh && echo "  ✓ Removed deploy.sh (replaced by SAM)"

echo ""
echo -e "${YELLOW}Removing setup script...${NC}"
rm -f setup.sh && echo "  ✓ Removed setup.sh (covered by README.md)"

echo ""
echo -e "${YELLOW}Removing macOS artifacts...${NC}"
DSSTORE_COUNT=$(find . -name ".DS_Store" | wc -l)
find . -name ".DS_Store" -delete
echo "  ✓ Removed ${DSSTORE_COUNT} .DS_Store file(s)"

# Optional: Archive historical documentation
echo ""
echo -e "${BLUE}Historical documentation found:${NC}"
if [ -f "PHASE_2_COMPLETE.md" ] || [ -f "PHASE_3_COMPLETE.md" ]; then
    echo "  • PHASE_2_COMPLETE.md"
    echo "  • PHASE_3_COMPLETE.md"
    echo ""
    read -p "Archive these to docs/history/? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p docs/history
        [ -f "PHASE_2_COMPLETE.md" ] && mv PHASE_2_COMPLETE.md docs/history/ && echo "  ✓ Moved PHASE_2_COMPLETE.md"
        [ -f "PHASE_3_COMPLETE.md" ] && mv PHASE_3_COMPLETE.md docs/history/ && echo "  ✓ Moved PHASE_3_COMPLETE.md"
    else
        echo "  Keeping in root directory"
    fi
else
    echo "  (Already archived or removed)"
fi

# Count files after
AFTER_COUNT=$(find . -maxdepth 1 -type f | wc -l)
REMOVED=$((BEFORE_COUNT - AFTER_COUNT))

echo ""
echo "======================================"
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""
echo "Files removed: ${REMOVED}"
echo ""
echo -e "${YELLOW}⚠️  Next steps:${NC}"
echo "  1. Verify tests still pass:"
echo "     ${BLUE}pytest tests/ -v${NC}"
echo ""
echo "  2. Verify SAM can build:"
echo "     ${BLUE}sam build${NC}"
echo ""
echo "  3. Commit the changes:"
echo "     ${BLUE}git add -A${NC}"
echo "     ${BLUE}git commit -m \"chore: Remove redundant development files (replaced by SAM and proper tests)\"${NC}"
echo ""
echo -e "${GREEN}Your project is now cleaner and better organized!${NC}"
