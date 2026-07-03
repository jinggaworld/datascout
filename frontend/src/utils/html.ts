/**
 * Strip HTML tags from a string, returning plain text.
 * Used to clean dataset descriptions from sources like Zenodo that return HTML.
 */
export function stripHtml(html: string): string {
  if (!html) return ''
  return html
    .replace(/<[^>]*>/g, '')        // Remove all HTML tags
    .replace(/&nbsp;/g, ' ')        // Non-breaking space
    .replace(/&amp;/g, '&')         // Ampersand
    .replace(/&lt;/g, '<')          // Less than
    .replace(/&gt;/g, '>')          // Greater than
    .replace(/&quot;/g, '"')        // Double quote
    .replace(/&#39;/g, "'")         // Single quote
    .replace(/&mdash;/g, '—')       // Em dash
    .replace(/&ndash;/g, '–')       // En dash
    .replace(/&hellip;/g, '…')      // Ellipsis
    .replace(/&rsquo;/g, "'")       // Right single quote
    .replace(/&lsquo;/g, "'")       // Left single quote
    .replace(/&rdquo;/g, '"')       // Right double quote
    .replace(/&ldquo;/g, '"')       // Left double quote
    .replace(/\s+/g, ' ')           // Collapse whitespace
    .trim()
}
