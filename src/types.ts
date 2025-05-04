// src/types.ts
export interface BookmarkType {
  id: number;
  url: string;
  created_at: string;
  updated_at: string | null;
  comment: string | null;
  folder_id: number | null;
  title: string;
  faviconColor?: string;
}

export interface FolderType {
  id: number;
  name: string;
  parent_id: number | null;
  color: string;
}

export interface FolderNode {
  folder: FolderType;
  children: FolderNode[];
  level: number;
}
