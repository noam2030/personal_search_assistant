export interface Task {
  id: number;
  user_id: str;
  name: string;
  url?: string | null;
  goal: string;
  last_run_at?: string | null;
  last_status?: 'SUCCESS' | 'FAILED' | 'Pending' | null;
  last_result?: string | null;
  last_error?: string | null;
  created_at: string;
}

export type str = string;

export interface CreateTaskPayload {
  user_id: string;
  goal: string;
  name?: string;
  url?: string;
}

export interface UpdateTaskPayload {
  goal?: string;
  name?: string;
  url?: string;
}
