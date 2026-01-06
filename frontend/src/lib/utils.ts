import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a date according to user preference
 * @param date - Date string or Date object
 * @param format - Date format preference (DD/MM/YYYY, DD/Month/YYYY, MM/DD/YYYY, or DD/MM/YY)
 * @param language - Language code for month names (en or ro)
 * @returns Formatted date string
 */
export function formatDate(date: string | Date | null | undefined, format: string = 'DD/MM/YYYY', language: string = 'en'): string {
  if (!date) return '';
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';
    
    const day = dateObj.getDate().toString().padStart(2, '0');
    const month = dateObj.getMonth() + 1; // 0-indexed
    const monthStr = month.toString().padStart(2, '0');
    const year = dateObj.getFullYear();
    const yearShort = year.toString().slice(-2);
    
    if (format === 'DD/Month/YYYY') {
      const monthNames: Record<string, string[]> = {
        en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
        ro: ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie', 'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie']
      };
      const monthName = (monthNames[language] || monthNames.en)[month - 1];
      return `${day}/${monthName}/${year}`;
    } else if (format === 'MM/DD/YYYY') {
      // American format
      return `${monthStr}/${day}/${year}`;
    } else if (format === 'DD/MM/YY') {
      // Short year format
      return `${day}/${monthStr}/${yearShort}`;
    }
    
    // Default DD/MM/YYYY format
    return `${day}/${monthStr}/${year}`;
  } catch (error) {
    console.error('[formatDate] Error formatting date:', error);
    return '';
  }
}

/**
 * Format a date for display using user preferences
 * @param date - Date string or Date object
 * @param dateFormat - Date format preference from user settings
 * @param language - Language code from user settings
 * @returns Formatted date string
 */
export function formatDateWithPreferences(
  date: string | Date | null | undefined,
  dateFormat?: string,
  language?: string
): string {
  return formatDate(date, dateFormat || 'DD/MM/YYYY', language || 'en');
}