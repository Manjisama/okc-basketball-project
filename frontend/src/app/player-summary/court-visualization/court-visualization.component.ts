import { Component, Input, OnChanges, SimpleChanges, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';

export type EventType = 'shot' | 'pass' | 'turnover';
export type ActionName = 'Pick & Roll' | 'Isolation' | 'Post-up' | 'Off-Ball Screen' | 'UNKNOWN';

export interface VizEventBase { 
  x: number | null; 
  y: number | null; 
  occurred_at?: string; 
  game_id?: string | number; 
  __action?: ActionName;  // 稳定动作标识
  __id?: string;          // 稳定事件ID
}

export interface VizShot extends VizEventBase { 
  eventType: 'shot'; 
  shot_result: 'make' | 'miss'; 
  points: 0 | 2 | 3; 
}

export interface VizPass extends VizEventBase { 
  eventType: 'pass'; 
  target_player_id?: string | number; 
}

export interface VizTurnover extends VizEventBase { 
  eventType: 'turnover'; 
  turnover_type?: string; 
}

export type VizEvent = VizShot | VizPass | VizTurnover;

interface RenderedEvent {
  id: string;
  event: VizEvent;
  x: number;
  y: number;
  action: ActionName;
  opacity: number;
}

interface CourtPaths {
  centerLine: string;
  threePointLine: string;
  freeThrowRect: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

@Component({
  selector: 'app-court-visualization',
  templateUrl: './court-visualization.component.html',
  styleUrls: ['./court-visualization.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CourtVisualizationComponent implements OnChanges {

  // 输入属性
  @Input() width = 600;
  @Input() height = 564;
  @Input() events: VizEvent[] = [];
  @Input() activeActions: ActionName[] = ['Pick & Roll', 'Isolation', 'Post-up', 'Off-Ball Screen', 'UNKNOWN'];
  @Input() activeEventTypes: EventType[] = ['shot', 'pass', 'turnover'];
  @Input() actionOf: (e: VizEvent) => ActionName = (e: any) => e.__action ?? 'UNKNOWN';
  @Input() maxPointsToRender = 3000;
  @Input() pointSize = 6;
  @Input() showTooltips = true;
  @Input() enableFiltering = true;

  // 组件状态
  filteredEvents: RenderedEvent[] = [];
  isSampled = false;
  tooltipEvent: RenderedEvent | null = null;
  tooltipPosition = { x: 0, y: 0 };

  // 常量
  private readonly COURT_FEET_WIDTH = 50;
  private readonly COURT_FEET_HEIGHT = 47;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['events'] || changes['activeActions'] || changes['activeEventTypes'] || 
        changes['actionOf'] || changes['maxPointsToRender']) {
      this.updateFilteredEvents();
      this.cdr.markForCheck();
    }
  }

  /**
   * 获取半场路径（动态计算）
   */
  get courtPaths(): CourtPaths {
    const W = this.width;
    const H = this.height;
    
    return {
      centerLine: `M ${W / 2} 0 L ${W / 2} ${H}`,
      threePointLine: `M 50 ${H * 0.2} A 100 100 0 0 1 ${W - 50} ${H * 0.2} L ${W - 50} ${H}`,
      freeThrowRect: {
        x: W * 0.2,
        y: H * 0.6,
        width: W * 0.6,
        height: H * 0.2
      }
    };
  }

  /**
   * 坐标转换：feet → pixels
   */
  feetToPx(x: number, y: number, W: number, H: number, FW = 50, FH = 47): { X: number, Y: number } {
    const scaleX = W / FW;
    const scaleY = H / FH;
    const X = (x + FW / 2) * scaleX;
    const Y = (FH / 2 - y) * scaleY;
    return { X, Y };
  }

  /**
   * 获取三角形路径（用于传球）
   */
  getTrianglePoints(centerX: number, centerY: number, size: number): string {
    const halfSize = size / 2;
    return `${centerX},${centerY - halfSize} ${centerX + halfSize},${centerY + halfSize} ${centerX - halfSize},${centerY + halfSize}`;
  }

  /**
   * 更新过滤后的事件列表
   */
  private updateFilteredEvents(): void {
    let filtered = this.events.filter(event => {
      // 过滤无效坐标
      if (event.x === null || event.y === null) return false;
      
      // 过滤事件类型
      if (!this.activeEventTypes.includes(event.eventType)) return false;
      
      // 过滤动作类型
      const action = this.actionOf(event);
      if (!this.activeActions.includes(action)) return false;
      
      return true;
    });

    // 性能保护：限制渲染数量
    this.isSampled = filtered.length > this.maxPointsToRender;
    if (this.isSampled) {
      filtered = filtered.slice(0, this.maxPointsToRender);
    }

    // 转换为渲染对象
    this.filteredEvents = filtered.map((event) => {
      const coords = this.feetToPx(event.x!, event.y!, this.width, this.height);
      const action = this.actionOf(event);
      
      return {
        id: (event as any).__id || `event-${Math.random()}`,
        event,
        x: coords.X,
        y: coords.Y,
        action,
        opacity: this.isSampled ? 0.6 : 1.0
      };
    });
  }

  /**
   * 获取事件样式类
   */
  getEventClass(event: VizEvent): string {
    const baseClass = `event-${event.eventType}`;
    
    if (event.eventType === 'shot') {
      return `${baseClass} ${(event as VizShot).shot_result}`;
    }
    
    return baseClass;
  }

  /**
   * 获取事件颜色
   */
  getEventColor(event: VizEvent): string {
    switch (event.eventType) {
      case 'shot': return (event as VizShot).shot_result === 'make' ? '#4CAF50' : '#F44336';
      case 'pass': return '#2196F3';
      case 'turnover': return '#FF9800';
      default: return '#757575';
    }
  }

  /**
   * 显示tooltip
   */
  showTooltip(event: RenderedEvent, mouseEvent: MouseEvent): void {
    if (!this.showTooltips) return;
    
    this.tooltipEvent = event;
    this.tooltipPosition = {
      x: mouseEvent.offsetX + 10,
      y: mouseEvent.offsetY - 10
    };
    this.cdr.markForCheck();
  }

  /**
   * 隐藏tooltip
   */
  hideTooltip(): void {
    this.tooltipEvent = null;
    this.cdr.markForCheck();
  }

  /**
   * 获取tooltip文本
   */
  getTooltipText(event: RenderedEvent): string {
    const { event: vizEvent, action } = event;
    
    switch (vizEvent.eventType) {
      case 'shot':
        const shot = vizEvent as VizShot;
        return `Shot ${shot.shot_result} (${shot.points}pt) in ${action}`;
      case 'pass':
        const pass = vizEvent as VizPass;
        const target = pass.target_player_id ? ` → #${pass.target_player_id}` : '';
        return `Pass${target} in ${action}`;
      case 'turnover':
        const turnover = vizEvent as VizTurnover;
        const type = turnover.turnover_type ? ` (${turnover.turnover_type})` : '';
        return `Turnover${type} in ${action}`;
      default:
        return `Event in ${action}`;
    }
  }

  /**
   * 获取事件统计
   */
  getEventStats(): { [key in EventType]: number } {
    const stats = { shot: 0, pass: 0, turnover: 0 };
    this.filteredEvents.forEach(item => {
      stats[item.event.eventType]++;
    });
    return stats;
  }

  /**
   * 切换事件类型过滤
   */
  toggleEventType(eventType: EventType): void {
    if (!this.enableFiltering) return;
    
    const index = this.activeEventTypes.indexOf(eventType);
    if (index > -1) {
      this.activeEventTypes = this.activeEventTypes.filter(et => et !== eventType);
    } else {
      this.activeEventTypes = [...this.activeEventTypes, eventType];
    }
    this.updateFilteredEvents();
    this.cdr.markForCheck();
  }

  /**
   * 切换动作类型过滤
   */
  toggleActionType(actionType: ActionName): void {
    if (!this.enableFiltering) return;
    
    const index = this.activeActions.indexOf(actionType);
    if (index > -1) {
      this.activeActions = this.activeActions.filter(at => at !== actionType);
    } else {
      this.activeActions = [...this.activeActions, actionType];
    }
    this.updateFilteredEvents();
    this.cdr.markForCheck();
  }

  /**
   * 检查事件类型是否激活
   */
  isEventTypeActive(eventType: EventType): boolean {
    return this.activeEventTypes.includes(eventType);
  }

  /**
   * 检查动作类型是否激活
   */
  isActionTypeActive(actionType: ActionName): boolean {
    return this.activeActions.includes(actionType);
  }

  /**
   * TrackBy函数优化性能
   */
  trackByEventId = (_: number, item: RenderedEvent): string => {
    return (item.event as any).__id ?? item.id;
  };

  /**
   * 获取投篮填充状态（命中实心，未中空心）
   */
  getShotFill(event: VizShot): string {
    return event.shot_result === 'make' ? this.getEventColor(event) : 'none';
  }

  /**
   * 获取投篮描边颜色
   */
  getShotStroke(event: VizShot): string {
    return this.getEventColor(event);
  }
}
