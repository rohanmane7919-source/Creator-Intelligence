import { Database, GitCompare, History, LayoutDashboard, Search, ShieldAlert, Sparkles } from "lucide-react";

// ready: false pages show an honest "not built yet" screen with the planned scope.
export const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, ready: true },
  {
    to: "/discovery", label: "Creator discovery", icon: Search, ready: false, stage: 6,
    summary: "Search and filter every creator record in the database.",
    planned: ["Search by name or ID", "Filters for category, platform, follower range and engagement rate",
      "Sortable, paginated table with a creator detail view", "Clear markers for missing data"],
  },
  {
    to: "/recommendations", label: "AI recommendations", icon: Sparkles, ready: false, stage: 6,
    summary: "Rank creators for a campaign and explain every ranking.",
    planned: ["Campaign inputs: category, objective, follower range, minimum engagement",
      "A transparent rule-based score (labelled as rule-based, not machine learning)",
      "A plain-language reason for each recommended creator"],
  },
  {
    to: "/risk", label: "Trust and risk", icon: ShieldAlert, ready: false, stage: 7,
    summary: "Show data-quality and trust signals for each creator.",
    planned: ["Configurable risk score with an explanation", "Unusual metric patterns, shown as signals and never as proof of fraud",
      "Missing or inconsistent metrics"],
  },
  {
    to: "/compare", label: "Compare creators", icon: GitCompare, ready: false, stage: 6,
    summary: "Put selected creators side by side.",
    planned: ["Followers, engagement, likes, comments and views", "Category, platform and data completeness",
      "Trust and risk indicators"],
  },
  {
    to: "/data", label: "Data management", icon: Database, ready: false, stage: 10,
    summary: "Upload, check and import creator data from the browser.",
    planned: ["CSV upload with a preview", "Missing-value and duplicate reports", "Cleaning summary and import into PostgreSQL"],
  },
  {
    to: "/history", label: "Search history", icon: History, ready: false, stage: 10,
    summary: "Review past business searches and their results.",
    planned: ["Saved filters and timestamps", "The recommendations each search returned"],
  },
];
