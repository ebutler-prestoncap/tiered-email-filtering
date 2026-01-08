/**
 * Date formatting utilities with Pacific timezone support
 */

const PACIFIC_TIMEZONE = 'America/Los_Angeles';

/**
 * Format a date string to Pacific time
 * @param dateString - ISO date string or date string
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string in Pacific time
 */
export function formatDatePacific(
  dateString: string,
  options: Intl.DateTimeFormatOptions = {}
): string {
  const date = new Date(dateString);
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    timeZone: PACIFIC_TIMEZONE,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  };
  
  return date.toLocaleString('en-US', defaultOptions);
}

/**
 * Format a date to Pacific time (date only)
 * @param dateString - ISO date string or date string
 * @returns Formatted date string (e.g., "Jan 15, 2024")
 */
export function formatDateOnlyPacific(dateString: string): string {
  return formatDatePacific(dateString, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a date to Pacific time (date and time)
 * @param dateString - ISO date string or date string
 * @returns Formatted date and time string (e.g., "Jan 15, 2024, 2:30 PM")
 */
export function formatDateTimePacific(dateString: string): string {
  return formatDatePacific(dateString, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date to Pacific time (compact format)
 * @param dateString - ISO date string or date string
 * @returns Formatted date string (e.g., "1/15/2024, 2:30 PM")
 */
export function formatDateCompactPacific(dateString: string): string {
  return formatDatePacific(dateString, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

