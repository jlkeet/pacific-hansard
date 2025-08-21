export interface SearchResult {
  id: string;
  doc_id: string;
  text: string;
  speaker: string;
  date: string;
  country: string;
  chamber: string;
  url: string;
  score: number;
  chunk_index: number;
}
