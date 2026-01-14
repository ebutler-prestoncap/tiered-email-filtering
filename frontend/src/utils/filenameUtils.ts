/**
 * Utility functions for generating smart prefixes from filenames
 */

/**
 * Clean a filename to extract a meaningful prefix
 * Removes extensions, dates, and common suffixes
 * @param filename - The filename to clean
 * @returns Cleaned filename without extension
 */
function cleanFilename(filename: string): string {
  // Remove file extension
  let cleaned = filename.replace(/\.(xlsx|xls)$/i, '');
  
  // Remove common date patterns (YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD, etc.)
  cleaned = cleaned.replace(/[-_]?\d{4}[-_]?\d{2}[-_]?\d{2}/g, '');
  
  // Remove timestamps (HHMMSS, HH-MM-SS, etc.)
  cleaned = cleaned.replace(/[-_]?\d{6}/g, '');
  cleaned = cleaned.replace(/[-_]?\d{2}[-_]?\d{2}[-_]?\d{2}/g, '');
  
  // Remove common suffixes
  const commonSuffixes = [
    '_Tiered_List',
    '_TieredList',
    '_Tiered',
    '_List',
    '_Contacts',
    '_Contact',
    '_Combined',
    '-Tiered-List',
    '-TieredList',
    '-Tiered',
    '-List',
    '-Contacts',
    '-Contact',
    '-Combined',
  ];
  
  for (const suffix of commonSuffixes) {
    if (cleaned.endsWith(suffix)) {
      cleaned = cleaned.slice(0, -suffix.length);
      break;
    }
  }
  
  // Clean up multiple consecutive separators
  cleaned = cleaned.replace(/[-_]+/g, '-');
  cleaned = cleaned.replace(/^[-_]+|[-_]+$/g, '');
  
  return cleaned.trim();
}

/**
 * Find common words across multiple filenames
 * @param filenames - Array of cleaned filenames
 * @returns Array of common words
 */
function findCommonWords(filenames: string[]): string[] {
  if (filenames.length === 0) return [];
  if (filenames.length === 1) {
    return filenames[0].split(/[-_\s]+/).filter(w => w.length > 0);
  }
  
  // Split each filename into words
  const wordSets = filenames.map(name => {
    const words = name.split(/[-_\s]+/).filter(w => w.length > 0);
    return new Set(words.map(w => w.toLowerCase()));
  });
  
  // Find words that appear in all filenames
  const firstSet = wordSets[0];
  const commonWords: string[] = [];
  
  for (const word of firstSet) {
    if (wordSets.every(set => set.has(word))) {
      // Find the original capitalization from the first filename
      const originalWord = filenames[0]
        .split(/[-_\s]+/)
        .find(w => w.toLowerCase() === word);
      if (originalWord) {
        commonWords.push(originalWord);
      }
    }
  }
  
  return commonWords;
}

/**
 * Extract the first few words from a filename
 * @param filename - The cleaned filename
 * @param maxWords - Maximum number of words to extract (default: 2)
 * @returns First few words joined with hyphens
 */
function extractRootWords(filename: string, maxWords: number = 2): string {
  const words = filename.split(/[-_\s]+/).filter(w => w.length > 0);
  return words.slice(0, maxWords).join('-');
}

/**
 * Generate a smart prefix from one or more filenames
 * Uses only the first few words (root) of the filename(s)
 * @param filenames - Array of filenames (File objects or strings)
 * @returns Generated prefix string
 */
export function generatePrefixFromFilenames(filenames: (File | string)[]): string {
  if (filenames.length === 0) {
    return 'Combined-Contacts';
  }
  
  // Extract filename strings
  const filenameStrings = filenames.map(f => 
    typeof f === 'string' ? f : f.name
  );
  
  // Clean all filenames
  const cleanedNames = filenameStrings.map(cleanFilename);
  
  // Filter out empty names
  const validNames = cleanedNames.filter(name => name.length > 0);
  
  if (validNames.length === 0) {
    return 'Combined-Contacts';
  }
  
  // Single file: extract first 1-2 words
  if (validNames.length === 1) {
    const rootWords = extractRootWords(validNames[0], 2);
    return rootWords || 'Combined-Contacts';
  }
  
  // Multiple files: find common words, then take first few
  const commonWords = findCommonWords(validNames);
  
  if (commonWords.length > 0) {
    // Use first 2 common words joined with hyphens
    return commonWords.slice(0, 2).join('-');
  }
  
  // No common words: use first word from first file
  const firstWords = validNames[0].split(/[-_\s]+/).filter(w => w.length > 0);
  if (firstWords.length > 0) {
    return firstWords[0];
  }
  
  // Fallback
  return 'Combined-Contacts';
}

