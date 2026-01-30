import {
  Route,
  AIRouteSuggestion,
  SolarSystem,
  Skills,
  ShipFit,
  ZKillboardData,
} from "../types";
import ESIService from "./ESIService";
import ZKillboardService from "./ZKillboardService";

class AIService {
  // Calculate jump range for capital ships based on skills
  calculateJumpRange(
    baseRange: number,
    jumpDriveCalibrationLevel: number,
    jumpFreighterSkillLevel: number = 0,
  ): number {
    // JDC adds 20% per level, Jump Freighters adds 10% per level
    const jdcBonus = 1 + jumpDriveCalibrationLevel * 0.2;
    const jfBonus = 1 + jumpFreighterSkillLevel * 0.1;
    return baseRange * jdcBonus * jfBonus;
  }

  // Calculate route with jump-capable ships
  async calculateJumpRoute(
    origin: number,
    destination: number,
    jumpRange: number,
    fuelCapacity: number,
  ): Promise<Route> {
    // This is a simplified implementation
    // In a real scenario, this would use complex pathfinding algorithms
    const systems: number[] = [origin];
    let currentSystem = origin;

    while (currentSystem !== destination) {
      // Find systems within jump range
      // This would need a proper spatial database in production
      systems.push(destination);
      currentSystem = destination;
    }

    return {
      origin,
      destination,
      systems,
      jumps: systems.length - 1,
      route_type: "jump_capable",
    };
  }

  // Analyze route safety based on zkillboard data
  async analyzeRouteSafety(systemIds: number[]): Promise<string> {
    const dangerMap =
      await ZKillboardService.getRouteDangerAssessment(systemIds);

    let extremeDanger = 0;
    let highDanger = 0;
    let mediumDanger = 0;

    dangerMap.forEach((data) => {
      if (data.danger_rating === "extreme") extremeDanger++;
      else if (data.danger_rating === "high") highDanger++;
      else if (data.danger_rating === "medium") mediumDanger++;
    });

    if (extremeDanger > 0) {
      return `High Risk: ${extremeDanger} systems with extreme danger. Consider alternative route.`;
    } else if (highDanger > 2) {
      return `Medium Risk: ${highDanger} systems with high activity. Exercise caution.`;
    } else if (mediumDanger > 3) {
      return `Low-Medium Risk: ${mediumDanger} systems with moderate activity.`;
    }

    return "Low Risk: Route appears relatively safe.";
  }

  // Generate route suggestions with AI analysis
  async generateRouteSuggestions(
    origin: number,
    destination: number,
    avoidHighSec: boolean = false,
    useJumpDrive: boolean = false,
    jumpRange?: number,
  ): Promise<AIRouteSuggestion> {
    try {
      // Get shortest route
      const shortestRoute = await ESIService.getRoute(origin, destination);

      // Calculate alternative safer route (avoiding high-danger systems)
      const dangerMap =
        await ZKillboardService.getRouteDangerAssessment(shortestRoute);
      const dangerousSystems: number[] = [];

      dangerMap.forEach((data, systemId) => {
        if (data.danger_rating === "extreme" || data.danger_rating === "high") {
          dangerousSystems.push(systemId);
        }
      });

      let alternativeRoutes: Route[] = [];
      if (dangerousSystems.length > 0) {
        try {
          const saferRoute = await ESIService.getRoute(
            origin,
            destination,
            dangerousSystems,
          );
          alternativeRoutes.push({
            origin,
            destination,
            systems: saferRoute,
            jumps: saferRoute.length - 1,
            route_type: "safest",
            avoid_systems: dangerousSystems,
          });
        } catch (error) {
          // No alternative route available
        }
      }

      const mainRoute: Route = {
        origin,
        destination,
        systems: shortestRoute,
        jumps: shortestRoute.length - 1,
        route_type: "shortest",
      };

      const riskAssessment = await this.analyzeRouteSafety(shortestRoute);
      const estimatedTime = shortestRoute.length * 60; // 60 seconds per jump

      const warnings: string[] = [];
      dangerMap.forEach((data, systemId) => {
        if (data.danger_rating === "extreme") {
          warnings.push(
            `System ${systemId}: Extreme danger - ${data.kills_last_hour} kills in last hour`,
          );
        } else if (data.danger_rating === "high") {
          warnings.push(
            `System ${systemId}: High danger - ${data.kills_last_hour} kills in last hour`,
          );
        }
      });

      return {
        route: mainRoute,
        risk_assessment: riskAssessment,
        estimated_time: estimatedTime,
        alternative_routes: alternativeRoutes,
        warnings,
      };
    } catch (error) {
      console.error("Error generating route suggestions:", error);
      throw error;
    }
  }

  // Suggest ship fittings based on character skills and intended use
  async suggestShipFit(
    shipTypeId: number,
    purpose: "pvp" | "pve" | "exploration" | "hauling" | "mining",
    skills?: Skills,
  ): Promise<ShipFit[]> {
    // This is a placeholder for AI-powered fit suggestions
    // In production, this would query a database of proven fits
    // and filter based on character skills

    const suggestions: ShipFit[] = [];

    // This would be populated from a fit database or API
    // For now, return empty array as placeholder

    return suggestions;
  }

  // Analyze asset distribution and suggest consolidation
  analyzeAssetDistribution(assets: any[]): string {
    const locationMap = new Map<number, number>();

    assets.forEach((asset) => {
      const count = locationMap.get(asset.location_id) || 0;
      locationMap.set(asset.location_id, count + 1);
    });

    const locations = Array.from(locationMap.entries()).sort(
      (a, b) => b[1] - a[1],
    );

    if (locations.length > 10) {
      return `Assets are spread across ${locations.length} locations. Consider consolidating to reduce logistics complexity.`;
    } else if (locations.length > 5) {
      return `Assets are in ${locations.length} locations. Moderate consolidation recommended.`;
    }

    return `Assets are well-consolidated in ${locations.length} locations.`;
  }

  // Analyze market orders and suggest pricing adjustments
  analyzeMarketOrders(orders: any[], marketData: any[]): string {
    // Placeholder for market analysis
    const activeOrders = orders.filter((order) => order.volume_remain > 0);

    if (activeOrders.length === 0) {
      return "No active market orders.";
    }

    return `You have ${activeOrders.length} active market orders. Monitor competition for pricing adjustments.`;
  }
}

export default new AIService();
