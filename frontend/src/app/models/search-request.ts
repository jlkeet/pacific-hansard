export interface SearchRequest {
  query: string;
  top_k: number;
  filters: {
    country?: string;
    speaker?: string;
    chamber?: string;
    date_from?: string;
    date_to?: string;
  };
}
