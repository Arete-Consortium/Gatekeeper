import axios, { AxiosInstance } from "axios";
import { ZKillboardData, KillmailSummary } from "../types";
import { API_CONFIG } from "../config";

class ZKillboardService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.ZKILLBOARD_BASE_URL,
      headers: {
        "User-Agent": "Eve-Nexus-App/1.0",
      },
    });
  }

  async getSystemKills(
    systemId: number,
    hoursBack: number = 1,
  ): Promise<KillmailSummary[]> {
    try {
      const response = await this.client.get(
        `/kills/solarSystemID/${systemId}/`,
      );
      const kills = response.data || [];

      // Filter kills by time
      const cutoffTime = new Date();
      cutoffTime.setHours(cutoffTime.getHours() - hoursBack);

      return kills
        .filter((kill: any) => new Date(kill.killmail_time) > cutoffTime)
        .map((kill: any) => ({
          killmail_id: kill.killmail_id,
          killmail_time: kill.killmail_time,
          solar_system_id: kill.solar_system_id,
          victim_ship_type_id: kill.victim?.ship_type_id,
          total_value: kill.zkb?.totalValue || 0,
        }));
    } catch (error) {
      console.error(`Error fetching kills for system ${systemId}:`, error);
      return [];
    }
  }

  async getSystemDangerRating(systemId: number): Promise<ZKillboardData> {
    const kills = await this.getSystemKills(systemId, 1);
    const killCount = kills.length;

    let dangerRating: "low" | "medium" | "high" | "extreme" = "low";
    if (killCount > 20) {
      dangerRating = "extreme";
    } else if (killCount > 10) {
      dangerRating = "high";
    } else if (killCount > 5) {
      dangerRating = "medium";
    }

    return {
      system_id: systemId,
      kills_last_hour: killCount,
      danger_rating: dangerRating,
      recent_kills: kills.slice(0, 10), // Return top 10 recent kills
    };
  }

  async getRouteDangerAssessment(
    systemIds: number[],
  ): Promise<Map<number, ZKillboardData>> {
    const dangerMap = new Map<number, ZKillboardData>();

    // Fetch danger ratings for each system in parallel
    const promises = systemIds.map(async (systemId) => {
      const dangerData = await this.getSystemDangerRating(systemId);
      dangerMap.set(systemId, dangerData);
    });

    await Promise.all(promises);
    return dangerMap;
  }

  async getCharacterKills(
    characterId: number,
    limit: number = 50,
  ): Promise<any[]> {
    try {
      const response = await this.client.get(
        `/kills/characterID/${characterId}/`,
        {
          params: { limit },
        },
      );
      return response.data || [];
    } catch (error) {
      console.error(
        `Error fetching kills for character ${characterId}:`,
        error,
      );
      return [];
    }
  }

  async getCorporationKills(
    corporationId: number,
    limit: number = 50,
  ): Promise<any[]> {
    try {
      const response = await this.client.get(
        `/kills/corporationID/${corporationId}/`,
        {
          params: { limit },
        },
      );
      return response.data || [];
    } catch (error) {
      console.error(
        `Error fetching kills for corporation ${corporationId}:`,
        error,
      );
      return [];
    }
  }
}

export default new ZKillboardService();
