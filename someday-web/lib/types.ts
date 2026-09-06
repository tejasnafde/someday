export type TaskStatus = "saved" | "interested" | "planned" | "done" | "archived";
export type Category = "watch" | "eat" | "visit" | "read" | "play" | "trip" | "talk" | "other";

export interface TourState {
  seen: string[];
}

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  tour_state?: TourState | null;
}

export interface Circle {
  id: string;
  name: string;
  emoji: string | null;
  owner_id: string;
  invite_token: string;
  member_count: number;
  open_intent_count: number;
  created_at: string;
}

export interface Member {
  user_id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: "owner" | "admin" | "member";
  joined_at: string;
}

export interface CircleDetail extends Circle {
  members: Member[];
  moments_cadence?: number;
}

export interface MomentPost {
  id: string;
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  photo_url: string | null; // null while hidden by the reveal rule
  caption: string | null;
  tz: string;
  late: boolean;
  created_at: string;
}

export interface Moment {
  id: string;
  circle_id: string;
  moment_date: string;
  circle_name?: string;
  revealed: boolean;
  my_post?: MomentPost | null;
  posts: MomentPost[];
}

export interface LinkMeta {
  title: string | null;
  image: string | null;
  site: string | null;
  description?: string | null;
  /** Transient /unfurl responses only: the domain is known to block previews. */
  restricted_platform?: boolean;
}

export interface Intent {
  id: string;
  circle_id: string;
  created_by: string;
  title: string;
  url: string | null;
  note: string | null;
  category: Category | null;
  tags: string[];
  auto_tags?: string[];
  task_status: TaskStatus;
  link_meta: LinkMeta | null;
  planned_for: string | null;
  reaction_count: number;
  boosted_by_me: boolean | number;
  reacted_by_me: boolean | number;
  done_note: string | null;
  done_photos: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface AppNotification {
  id: string;
  type: string;
  body: string;
  seen: boolean;
  intent_id: string | null;
  created_at: string;
}

export interface NotificationFeed {
  unseen: number;
  items: AppNotification[];
}

export interface SmartPick {
  intent_id: string;
  title: string;
  link_meta: LinkMeta | null;
  score: number;
  breakdown: {
    mutual_ratio: number;
    reaction_count: number;
    days_saved: number;
    has_boost: boolean;
    points: { mutual: number; age: number; boost: number; total: number };
  };
}

export interface SpinItem {
  id: string;
  title: string;
  link_meta: LinkMeta | null;
  category: Category | null;
  reaction_count: number;
}
