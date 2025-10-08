import {
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  ViewEncapsulation
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { untilDestroyed, UntilDestroy } from '@ngneat/until-destroy';
import { take } from 'rxjs/operators';
import { 
  ApiPlayerSummary, 
  ComponentState, 
  ActionType,
  DEFAULT_ACTION_CONFIGS,
  DEFAULT_EVENT_CONFIGS 
} from './player-summary.types';
import { PlayerSummaryService } from './player-summary.service';
import { 
  VizEvent, 
  EventType, 
  ActionName 
} from './court-visualization/court-visualization.component';

@UntilDestroy()
@Component({
  selector: 'player-summary-component',
  templateUrl: './player-summary.component.html',
  styleUrls: ['./player-summary.component.scss'],
  encapsulation: ViewEncapsulation.None,
})
export class PlayerSummaryComponent implements OnInit, OnDestroy {

  // 组件状态
  state: ComponentState = {
    loading: false,
    error: null,
    data: null
  };

  // 球员ID输入
  playerIdInput: string = '';
  
  // 配置数据
  actionConfigs = DEFAULT_ACTION_CONFIGS;
  eventConfigs = DEFAULT_EVENT_CONFIGS;

  // 动作类型列表
  actionTypes: string[] = [];

  // Court visualization data
  vizEvents: VizEvent[] = [];
  selectedActions: ActionName[] = ['Pick & Roll', 'Isolation', 'Post-up', 'Off-Ball Screen', 'UNKNOWN'];
  selectedEventTypes: EventType[] = ['shot', 'pass', 'turnover'];

  constructor(
    private activatedRoute: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private playerSummaryService: PlayerSummaryService,
  ) {
    this.actionTypes = this.playerSummaryService.getActionTypes();
  }

  ngOnInit(): void {
    // 从路由参数获取playerID
    this.activatedRoute.queryParamMap.pipe(
      take(1),
      untilDestroyed(this)
    ).subscribe(params => {
      const playerID = params.get('playerID');
      if (playerID) {
        this.playerIdInput = playerID;
        this.fetchPlayerData(playerID);
      }
    });

    // 检查服务配置
    const config = this.playerSummaryService.checkConfiguration();
    if (!config.isValid) {
      console.warn('Service configuration issue:', config.message);
    }
  }

  /**
   * 获取球员数据
   * @param playerID 球员ID
   */
  fetchPlayerData(playerID: string | number): void {
    if (!this.playerSummaryService.isValidPlayerID(playerID)) {
      this.setError('Invalid player ID. Please enter a valid number.');
      return;
    }

    this.setLoading(true);
    
    this.playerSummaryService.getPlayerSummary(playerID).pipe(
      untilDestroyed(this)
    ).subscribe({
      next: (data: ApiPlayerSummary) => {
        this.setData(data);
      },
      error: (error: Error) => {
        console.error('Component error:', error);
        this.setError(error.message || 'Failed to load player data');
      }
    });
  }

  /**
   * 手动搜索球员
   */
  onSearchPlayer(): void {
    const playerID = this.playerIdInput.trim();
    if (playerID) {
      this.fetchPlayerData(playerID);
    }
  }

  /**
   * 处理回车键搜索
   * @param event 键盘事件
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.onSearchPlayer();
    }
  }

  /**
   * 重试加载数据
   */
  onRetry(): void {
    if (this.playerIdInput.trim()) {
      this.fetchPlayerData(this.playerIdInput.trim());
    }
  }

  /**
   * 清除错误状态
   */
  onClearError(): void {
    this.state.error = null;
    this.cdr.detectChanges();
  }

  /**
   * 获取动作组数据
   * @param actionKey 动作类型键名
   * @returns 动作组数据
   */
  getActionData(actionKey: string): any {
    if (!this.state.data?.actions) return null;
    return this.state.data.actions[actionKey as keyof typeof this.state.data.actions] || null;
  }

  /**
   * 格式化坐标显示
   * @param x x坐标
   * @param y y坐标
   * @returns 格式化后的坐标字符串
   */
  formatCoordinate(x: number | null, y: number | null): string {
    return this.playerSummaryService.formatCoordinate(x, y);
  }

  /**
   * 格式化排名显示
   * @param rank 排名
   * @returns 格式化后的排名字符串
   */
  formatRank(rank: number | null | undefined): string {
    return this.playerSummaryService.formatRank(rank);
  }

  /**
   * 格式化分数显示
   * @param points 分数
   * @returns 格式化后的分数字符串
   */
  formatPoints(points: number): string {
    return this.playerSummaryService.formatPoints(points);
  }

  /**
   * 获取动作类型显示名称
   * @param actionKey 动作类型键名
   * @returns 显示名称
   */
  getActionDisplayName(actionKey: string): string {
    return this.playerSummaryService.getActionDisplayName(actionKey);
  }

  /**
   * 检查动作组是否有数据
   * @param actionKey 动作类型键名
   * @returns 是否有有效数据
   */
  hasActionData(actionKey: string): boolean {
    const actionData = this.getActionData(actionKey);
    return this.playerSummaryService.hasActionData(actionData);
  }

  /**
   * 检查是否有数据
   * @returns 是否有数据
   */
  hasData(): boolean {
    return this.state.data !== null && !this.state.loading && !this.state.error;
  }

  /**
   * 检查是否为空数据
   * @returns 是否为空数据
   */
  isEmptyData(): boolean {
    if (!this.state.data) return false;
    
    const { totals } = this.state.data;
    return totals.points === 0 && 
           totals.passes === 0 && 
           totals.turnovers === 0 &&
           totals.makes === 0 &&
           totals.misses === 0;
  }

  /**
   * 获取事件数量
   * @param actionKey 动作类型键名
   * @param eventType 事件类型
   * @returns 事件数量
   */
  getEventCount(actionKey: string, eventType: 'shots' | 'passes' | 'turnovers'): number {
    const actionData = this.getActionData(actionKey);
    if (!actionData || !actionData[eventType]) return 0;
    return actionData[eventType].length;
  }

  /**
   * 获取示例事件（用于显示）
   * @param actionKey 动作类型键名
   * @param eventType 事件类型
   * @param limit 限制数量
   * @returns 示例事件数组
   */
  getSampleEvents(actionKey: string, eventType: 'shots' | 'passes' | 'turnovers', limit: number = 3): any[] {
    const actionData = this.getActionData(actionKey);
    if (!actionData || !actionData[eventType]) return [];
    return actionData[eventType].slice(0, limit);
  }

  /**
   * 数据拉平：将API结构转换为可视化事件数组
   * @param summary API响应数据
   * @returns 扁平化的事件数组
   */
  private flattenEvents(summary: ApiPlayerSummary): VizEvent[] {
    const result: VizEvent[] = [];
    const actions: ActionName[] = ['Pick & Roll', 'Isolation', 'Post-up', 'Off-Ball Screen', 'UNKNOWN'];
    
    actions.forEach(action => {
      const actionData = summary.actions[action];
      if (!actionData) return;
      
      // 处理投篮
      actionData.shots?.forEach((shot, index) => {
        if (shot.x !== null && shot.y !== null) {
          const eventId = `${summary.playerId}-${action}-shot-${index}-${shot.occurred_at ?? ''}`;
          result.push({
            eventType: 'shot',
            x: shot.x,
            y: shot.y,
            shot_result: shot.shot_result,
            points: shot.points,
            occurred_at: shot.occurred_at,
            game_id: shot.game_id,
            __action: action,
            __id: eventId
          } as any);
        }
      });
      
      // 处理传球
      actionData.passes?.forEach((pass, index) => {
        if (pass.x !== null && pass.y !== null) {
          const eventId = `${summary.playerId}-${action}-pass-${index}-${pass.occurred_at ?? ''}`;
          result.push({
            eventType: 'pass',
            x: pass.x,
            y: pass.y,
            target_player_id: pass.target_player_id,
            occurred_at: pass.occurred_at,
            game_id: pass.game_id,
            __action: action,
            __id: eventId
          } as any);
        }
      });
      
      // 处理失误
      actionData.turnovers?.forEach((turnover, index) => {
        if (turnover.x !== null && turnover.y !== null) {
          const eventId = `${summary.playerId}-${action}-turnover-${index}-${turnover.occurred_at ?? ''}`;
          result.push({
            eventType: 'turnover',
            x: turnover.x,
            y: turnover.y,
            turnover_type: turnover.turnover_type,
            occurred_at: turnover.occurred_at,
            game_id: turnover.game_id,
            __action: action,
            __id: eventId
          } as any);
        }
      });
    });
    
    return result;
  }

  /**
   * 动作映射函数（用于court visualization）
   * @param event 可视化事件
   * @returns 动作类型
   */
  actionOf = (event: VizEvent): ActionName => {
    return (event as any).__action ?? 'UNKNOWN';
  };

  // 私有辅助方法
  private setLoading(loading: boolean): void {
    this.state.loading = loading;
    this.state.error = null;
    this.cdr.detectChanges();
  }

  private setData(data: ApiPlayerSummary): void {
    this.state.data = data;
    this.vizEvents = this.flattenEvents(data);
    this.state.loading = false;
    this.state.error = null;
    this.cdr.detectChanges();
  }

  private setError(error: string): void {
    this.state.error = error;
    this.state.loading = false;
    this.state.data = null;
    this.cdr.detectChanges();
  }

  ngOnDestroy(): void {
    // untilDestroyed 自动处理订阅清理
  }
}