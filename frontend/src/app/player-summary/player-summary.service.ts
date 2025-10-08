import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { catchError, retry, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { ApiPlayerSummary, ApiErrorResponse } from './player-summary.types';

/**
 * Player Summary Service
 * 
 * Handles all API calls for player summary data with proper error handling
 * and environment configuration.
 */
@Injectable({
  providedIn: 'root'
})
export class PlayerSummaryService {
  
  private readonly baseUrl: string;
  private readonly retryAttempts = 1;

  constructor(private http: HttpClient) {
    // 从environment获取后端域名，确保末尾没有斜杠
    this.baseUrl = environment.BACKEND_PUBLIC_DOMAIN?.replace(/\/$/, '') || '';
    
    if (!this.baseUrl) {
      console.warn('BACKEND_PUBLIC_DOMAIN not configured in environment');
    }
  }

  /**
   * 获取球员汇总数据
   * @param playerID 球员ID (string | number)
   * @returns Observable<ApiPlayerSummary>
   */
  getPlayerSummary(playerID: string | number): Observable<ApiPlayerSummary> {
    const url = `${this.baseUrl}/api/v1/playerSummary/${encodeURIComponent(String(playerID))}`;
    
    console.log(`Fetching player summary from: ${url}`);
    
    return this.http.get<ApiPlayerSummary>(url).pipe(
      // 可选：瞬时错误重试一次
      retry(this.retryAttempts),
      map((response: ApiPlayerSummary) => {
        console.log('Player summary response:', response);
        return response;
      }),
      catchError((error: HttpErrorResponse) => {
        console.error('Error fetching player summary:', error);
        
        // 统一错误处理
        const errorMessage = this.handleHttpError(error);
        return throwError(() => new Error(errorMessage));
      })
    );
  }

  /**
   * 验证球员ID格式
   * @param playerID 球员ID
   * @returns boolean
   */
  isValidPlayerID(playerID: string | number): boolean {
    if (!playerID) return false;
    
    const id = typeof playerID === 'string' ? playerID.trim() : String(playerID);
    
    // 检查是否为有效数字
    const numericId = parseFloat(id);
    return !isNaN(numericId) && numericId > 0 && Number.isInteger(numericId);
  }

  /**
   * 格式化坐标显示
   * @param x x坐标
   * @param y y坐标
   * @param precision 小数位数
   * @returns 格式化后的坐标字符串
   */
  formatCoordinate(x: number | null, y: number | null, precision: number = 1): string {
    if (x === null || y === null) {
      return '—';
    }
    return `(${x.toFixed(precision)}, ${y.toFixed(precision)})`;
  }

  /**
   * 格式化排名显示
   * @param rank 排名
   * @returns 格式化后的排名字符串
   */
  formatRank(rank: number | null | undefined): string {
    if (rank === null || rank === undefined) {
      return 'N/A';
    }
    return `#${rank}`;
  }

  /**
   * 格式化分数显示
   * @param points 分数
   * @returns 格式化后的分数字符串
   */
  formatPoints(points: number): string {
    return `${points} pts`;
  }

  /**
   * 获取动作类型显示名称
   * @param actionKey 动作类型键名
   * @returns 显示名称
   */
  getActionDisplayName(actionKey: string): string {
    // 动作键名与显示名称一致，直接返回
    return actionKey;
  }

  /**
   * 检查动作组是否有数据
   * @param actionGroup 动作组数据
   * @returns 是否有有效数据
   */
  hasActionData(actionGroup: any): boolean {
    if (!actionGroup) return false;
    
    const { shots, passes, turnovers, totals } = actionGroup;
    
    return (
      (shots && shots.length > 0) ||
      (passes && passes.length > 0) ||
      (turnovers && turnovers.length > 0) ||
      (totals && Object.values(totals).some(val => val > 0))
    );
  }

  /**
   * 获取动作类型列表（按优先级排序）
   * @returns 动作类型键名数组
   */
  getActionTypes(): string[] {
    return [
      'Pick & Roll',
      'Isolation', 
      'Post-up',
      'Off-Ball Screen',
      'UNKNOWN'
    ];
  }

  /**
   * 处理HTTP错误
   * @param error HTTP错误响应
   * @returns 错误消息
   */
  private handleHttpError(error: HttpErrorResponse): string {
    console.error('HTTP Error Details:', {
      status: error.status,
      statusText: error.statusText,
      url: error.url,
      error: error.error
    });

    // 根据HTTP状态码返回相应的错误消息
    switch (error.status) {
      case 0:
        return 'Network error. Please check your connection and try again.';
      case 400:
        return 'Invalid player ID. Please enter a valid number.';
      case 404:
        return 'Player not found. Please check the player ID and try again.';
      case 500:
        return 'Server error. Please try again later.';
      case 503:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        // 尝试从错误响应中提取消息
        if (error.error?.message) {
          return error.error.message;
        }
        if (error.statusText) {
          return `${error.status}: ${error.statusText}`;
        }
        return 'An unexpected error occurred. Please try again.';
    }
  }

  /**
   * 获取API基础URL（用于调试）
   * @returns API基础URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * 检查服务配置
   * @returns 配置状态
   */
  checkConfiguration(): { isValid: boolean; baseUrl: string; message?: string } {
    if (!this.baseUrl) {
      return {
        isValid: false,
        baseUrl: '',
        message: 'BACKEND_PUBLIC_DOMAIN not configured in environment'
      };
    }

    return {
      isValid: true,
      baseUrl: this.baseUrl
    };
  }
}
