export interface ChatMessage {
  id: string;
  content: string;
  timestamp: Date;
  isUser: boolean;
  isLoading?: boolean;
  sources?: Array<{
    id: string;
    text: string;
    text_preview: string;
    full_text: string;
    country: string;
    date: string;
    speaker: string;
    url?: string;
    doc_id?: string;
    chunk_index?: number;
  }>;
}
