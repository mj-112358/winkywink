export interface ShelfInteraction {
  name: string;
  interactions: number;
}

export interface ShelfInteractionsData {
  as_of: string;
  shelves: ShelfInteraction[];
}

export interface AisleDwell {
  name: string;
  avg_dwell_seconds: number;
}

export interface DwellTimesData {
  as_of: string;
  aisles: AisleDwell[];
}

export interface FootfallEntry {
  date: string;
  footfall: number;
}

export interface FootfallDailyData {
  store_id: string;
  series: FootfallEntry[];
}

export interface GiftsHistoryEntry {
  date: string;
  Gifts: number;
}

export interface AisleFootfallChange {
  baseline: number;
  current: number;
}

export interface InsightsInputData {
  festival: {
    name: string;
    date: string;
  };
  shelf_interactions: {
    baseline_window_days: number;
    current: Record<string, number>;
    history: GiftsHistoryEntry[];
  };
  dwell: Record<string, number>;
  footfall_daily: number[];
  aisle_footfall_change: Record<string, AisleFootfallChange>;
}

export interface GeneratedInsight {
  title: string;
  description: string;
  type: 'festival' | 'aisle' | 'inventory' | 'staffing' | 'promo' | 'cross-sell';
  priority: 'high' | 'medium' | 'low';
}
