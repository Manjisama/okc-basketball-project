/**
 * Player Summary Types
 * 
 * These interfaces are designed to match the backend API response exactly,
 * including key names with spaces and null values.
 */

// 事件接口 - 与后端数据库字段对齐
export interface ShotEvent {
  x: number | null;
  y: number | null;
  shot_result: 'make' | 'miss';
  points: 0 | 2 | 3;
  game_id?: string | number;
  occurred_at?: string;
}

export interface PassEvent {
  x: number | null;
  y: number | null;
  target_player_id?: number | string | null;
  occurred_at?: string;
}

export interface TurnoverEvent {
  x: number | null;
  y: number | null;
  turnover_type?: string;
  occurred_at?: string;
}

// 动作组统计接口
export interface ActionGroup {
  shots: ShotEvent[];
  passes: PassEvent[];
  turnovers: TurnoverEvent[];
  totals: {
    shots: number;
    makes: number;
    misses: number;
    passes: number;
    turnovers: number;
    points: number;
  };
}

// 总体统计接口
export interface PlayerTotals {
  points: number;
  makes: number;
  misses: number;
  passes: number;
  turnovers: number;
  // 可以扩展其他统计字段
}

// 排名接口 - 允许null值
export interface PlayerRanks {
  points?: number | null;
  makes?: number | null;
  misses?: number | null;
  passes?: number | null;
  turnovers?: number | null;
  // 可以扩展其他排名字段
}

// 主API响应接口 - 与后端完全一致
export interface ApiPlayerSummary {
  playerId: number | string;
  totals: PlayerTotals;
  ranks: PlayerRanks;
  actions: {
    // 注意：动作名包含空格，必须用引号保持一致性
    'Pick & Roll'?: ActionGroup;
    'Isolation'?: ActionGroup;
    'Post-up'?: ActionGroup;
    'Off-Ball Screen'?: ActionGroup;
    'UNKNOWN'?: ActionGroup; // 可选分组
  };
}

// 动作类型枚举 - 用于前端显示
export enum ActionType {
  PICK_AND_ROLL = 'Pick & Roll',
  ISOLATION = 'Isolation',
  POST_UP = 'Post-up',
  OFF_BALL_SCREEN = 'Off-Ball Screen',
  UNKNOWN = 'UNKNOWN'
}

// 动作类型显示配置
export interface ActionTypeConfig {
  key: string;
  displayName: string;
  color?: string;
  icon?: string;
}

// 组件状态接口
export interface ComponentState {
  loading: boolean;
  error: string | null;
  data: ApiPlayerSummary | null;
}

// 错误响应接口
export interface ApiErrorResponse {
  message: string;
  status: number;
  timestamp?: string;
}

// 坐标格式化选项
export interface CoordinateFormatOptions {
  precision?: number;
  nullDisplay?: string;
}

// 事件类型枚举
export enum EventType {
  SHOT = 'shot',
  PASS = 'pass',
  TURNOVER = 'turnover'
}

// 事件显示配置
export interface EventDisplayConfig {
  type: EventType;
  displayName: string;
  color: string;
  icon: string;
}

// 默认动作类型配置
export const DEFAULT_ACTION_CONFIGS: ActionTypeConfig[] = [
  {
    key: ActionType.PICK_AND_ROLL,
    displayName: 'Pick & Roll',
    color: '#2196F3',
    icon: 'swap_horiz'
  },
  {
    key: ActionType.ISOLATION,
    displayName: 'Isolation',
    color: '#FF9800',
    icon: 'person'
  },
  {
    key: ActionType.POST_UP,
    displayName: 'Post-up',
    color: '#4CAF50',
    icon: 'backup'
  },
  {
    key: ActionType.OFF_BALL_SCREEN,
    displayName: 'Off-Ball Screen',
    color: '#9C27B0',
    icon: 'filter_list'
  },
  {
    key: ActionType.UNKNOWN,
    displayName: 'Unknown',
    color: '#757575',
    icon: 'help'
  }
];

// 默认事件显示配置
export const DEFAULT_EVENT_CONFIGS: EventDisplayConfig[] = [
  {
    type: EventType.SHOT,
    displayName: 'Shot',
    color: '#F44336',
    icon: 'sports_basketball'
  },
  {
    type: EventType.PASS,
    displayName: 'Pass',
    color: '#2196F3',
    icon: 'send'
  },
  {
    type: EventType.TURNOVER,
    displayName: 'Turnover',
    color: '#FF9800',
    icon: 'error'
  }
];

// 工具函数类型
export type CoordinateFormatter = (x: number | null, y: number | null) => string;
export type RankFormatter = (rank: number | null | undefined) => string;
export type PointsFormatter = (points: number) => string;
