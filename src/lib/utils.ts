export function createSalarySlug(salary: string): string {
  if (!salary) return '';
  return salary
    .toLowerCase()
    .replace(/£/g, '')
    .replace(/\+/g, 'plus')
    .replace(/,/g, '')
    .replace(/\s+-\s+/g, '-')
    .replace(/\s+/g, '-');
}

const NON_LOCATION_KEYWORDS = ['remote', 'national', 'various', 'flexible', 'unspecified', 'home-based'];

export function isValidLocation(location: string): boolean {
  if (!location) return false;
  
  const lowerCaseLoc = location.toLowerCase();
  const wordCount = lowerCaseLoc.split(' ').length;
  
  // Filter out long strings and common non-location keywords
  if (wordCount > 4) return false;
  if (NON_LOCATION_KEYWORDS.some(keyword => lowerCaseLoc.includes(keyword))) return false;
  
  return true;
}
