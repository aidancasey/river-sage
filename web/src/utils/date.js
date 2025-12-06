/**
 * Date utility functions using date-fns
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns';

/**
 * Format a timestamp to a readable date/time string
 * @param {string} timestamp - ISO 8601 timestamp
 * @param {string} formatString - date-fns format string
 * @returns {string} Formatted date string
 */
export function formatTimestamp(timestamp, formatString = 'PPpp') {
  try {
    const date = parseISO(timestamp);
    return format(date, formatString);
  } catch (error) {
    console.error('Error formatting timestamp:', error);
    return timestamp;
  }
}

/**
 * Get relative time string (e.g., "5 minutes ago")
 * @param {string} timestamp - ISO 8601 timestamp
 * @returns {string} Relative time string
 */
export function getRelativeTime(timestamp) {
  try {
    const date = parseISO(timestamp);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    console.error('Error calculating relative time:', error);
    return 'unknown';
  }
}

/**
 * Format data age in minutes to human-readable string
 * @param {number} minutes - Age in minutes
 * @returns {string} Human-readable age string
 */
export function formatDataAge(minutes) {
  if (minutes < 1) {
    return 'just now';
  } else if (minutes === 1) {
    return '1 minute ago';
  } else if (minutes < 60) {
    return `${minutes} minutes ago`;
  } else if (minutes < 120) {
    return '1 hour ago';
  } else {
    const hours = Math.floor(minutes / 60);
    return `${hours} hours ago`;
  }
}

export default {
  formatTimestamp,
  getRelativeTime,
  formatDataAge,
};
