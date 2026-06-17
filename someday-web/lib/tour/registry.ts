// Tour step registry — the single place new feature tours are added.
//
// To ship a tour for a new feature:
//   1. Add `data-tour="<anchor>"` to the feature's target element.
//   2. Append a step here with a stable, never-reused id.
// Users' seen step ids live server-side (users.tour_state), so anyone who
// hasn't seen the new step gets a mini-tour of just that step on next visit.

export type TourPage = "dashboard" | "circle" | "intent" | "members";

export interface TourStep {
  /** Stable forever — never rename or reuse. */
  id: string;
  page: TourPage;
  /** Matches data-tour="..." on the target element. */
  anchor: string;
  title: string;
  body: string;
}

export const TOUR_REGISTRY: TourStep[] = [
  {
    id: "dash.welcome",
    page: "dashboard",
    anchor: "logo",
    title: "Welcome to Someday",
    body: "All the things you keep saying “we should do that” — this is where they finally get planned. Here’s a quick look around.",
  },
  {
    id: "dash.create",
    page: "dashboard",
    anchor: "create-circle",
    title: "Start a circle",
    body: "A circle is you and the people you make plans with — movie nights, the trip group, your best friend.",
  },
  {
    id: "dash.settings",
    page: "dashboard",
    anchor: "settings",
    title: "Make it yours",
    body: "Set your name in Settings. You can replay this tour from there anytime.",
  },
  {
    id: "circle.add",
    page: "circle",
    anchor: "add-intent",
    title: "Save an idea",
    body: "Drop in links, places, films — anything you should get around to together.",
  },
  {
    id: "circle.status",
    page: "circle",
    anchor: "status-tabs",
    title: "From saved to done",
    body: "Ideas move from saved to interested to planned to done. Shortlist shows what more than one of you wants.",
  },
  {
    id: "circle.reactions",
    page: "circle",
    anchor: "intent-card",
    title: "Show you’re in",
    body: "Tap the heart when you’re interested. Boost something to nudge the group.",
  },
  {
    id: "circle.payoff",
    page: "circle",
    anchor: "payoff",
    title: "Can’t decide?",
    body: "Smart-pick scores what you’re all into — or spin the wheel and let fate pick tonight’s plan.",
  },
  {
    id: “circle.invite”,
    page: “circle”,
    anchor: “invite”,
    title: “Bring them in”,
    body: “Share an invite link — ideas are better when someone else says “yes, let’s”.”,
  },
  {
    id: “circle.tags”,
    page: “circle”,
    anchor: “tag-filter”,
    title: “Filter by tag”,
    body: “Tagged an idea? Tap a tag here to cut through a long list and find it fast.”,
  },
  {
    id: “intent.planned”,
    page: “intent”,
    anchor: “intent-planned”,
    title: “Set a date”,
    body: “Add a rough ‘when’ — next weekend, after exams — so it doesn’t stay a someday forever.”,
  },
  {
    id: “members.roles”,
    page: “members”,
    anchor: “members-list”,
    title: “Manage the circle”,
    body: “Promote someone to admin, remove a member, or grab the invite link to bring a new person in.”,
  },
  {
    id: “intent.memories”,
    page: “intent”,
    anchor: “intent-memories”,
    title: “Your memory lives here”,
    body: “When you mark something done, you can add a note and photos. A little record of actually doing it.”,
  },
];
