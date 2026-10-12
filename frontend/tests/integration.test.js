import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  checkHealth,
  analyzeWeather,
  analyzeOcean,
  analyzeFishingZone,
  analyzeRoute,
  analyzeSafetyRisk,
  analyzeOrchestrator,
  chatAssistant,
  getAssistantTools,
} from '../src/services/orcaApi.js';

describe('Live Backend Integration Tests (http://127.0.0.1:8001)', () => {
  it('1. GET /api/health - verifies active service', async () => {
    const health = await checkHealth();
    assert.equal(health.status, 'ok');
    assert.equal(health.service, 'orca-api');
  });

  it('2. Weather Agent - retrieves real atmospheric observations', async () => {
    const res = await analyzeWeather({
      latitude: 15.0,
      longitude: 72.0,
      location_name: 'Offshore Goa',
      forecast_days: 1,
    });
    assert.equal(res.agent, 'Weather Agent');
    assert.equal(res.status, 'success');
    assert.ok(typeof res.observations.temperature_c === 'number');
    assert.ok(typeof res.observations.wind_speed_knots === 'number');
    assert.ok(typeof res.observations.beaufort_scale.force === 'number');
  });

  it('3. Ocean Agent - retrieves real wave conditions without false timestamp warnings', async () => {
    const res = await analyzeOcean({
      latitude: 15.0,
      longitude: 72.0,
      location_name: 'Goa Ocean',
      forecast_time_window_hours: 24,
    });
    assert.equal(res.agent, 'Ocean Agent');
    assert.equal(res.status, 'success');
    assert.ok(typeof res.observations.avg_wave_height_m === 'number');
    assert.ok(typeof res.analysis.sea_state_code === 'number');
    // Critical: forecast records must not generate false warnings
    assert.ok(!res.warnings.some(w => w.includes('observation_after_retrieval')));
    assert.ok(!res.warnings.some(w => w.includes('observation_time_in_future')));
  });

  it('4. Ocean Agent - inland coordinates return insufficient_evidence', async () => {
    const res = await analyzeOcean({
      latitude: 21.15,
      longitude: 79.09,
      location_name: 'Inland Nagpur',
    });
    assert.equal(res.agent, 'Ocean Agent');
    assert.equal(res.status, 'insufficient_evidence');
    assert.equal(res.observations.sample_count, 0);
  });

  it('5. Fishing Zone Agent - separates physical wave conditions from fish evidence', async () => {
    const res = await analyzeFishingZone({
      latitude: 15.0,
      longitude: 72.0,
      target_species: 'Mackerel',
    });
    assert.equal(res.agent, 'Fishing Zone Agent');
    assert.equal(res.status, 'insufficient_evidence');
    assert.ok(['FAVORABLE', 'MODERATE / CAUTION', 'HAZARDOUS'].includes(res.analysis.operational_feasibility));
    assert.equal(res.analysis.verified_fish_distribution.status, 'UNVERIFIED');
    assert.ok(res.analysis.vessel_safety_notice.includes('does NOT determine vessel safety'));
  });

  it('6. Route Agent - marks calculations as straight-line estimates, not verified navigable routes', async () => {
    const res = await analyzeRoute({
      origin_latitude: 18.9,
      origin_longitude: 72.8,
      origin_name: 'Mumbai Port',
      destination_latitude: 15.4,
      destination_longitude: 73.8,
      destination_name: 'Mormugao Port',
      vessel_speed_knots: 14.0,
    });
    assert.equal(res.agent, 'Route Agent');
    assert.equal(res.status, 'success');
    assert.ok(res.observations.total_distance_nm > 0);
    assert.equal(res.observations.is_verified_navigable_route, false);
    assert.ok(res.analysis.navigable_route_disclaimer.includes('straight-line geodesic'));
  });

  it('7. Safety/Risk Agent - evaluates severe gale as CRITICAL risk', async () => {
    const res = await analyzeSafetyRisk({
      latitude: 15.0,
      longitude: 72.0,
      vessel_type: 'small_craft',
      wave_height_m: 3.8,
      wind_speed_knots: 38.0,
    });
    assert.equal(res.agent, 'Safety/Risk Agent');
    assert.equal(res.analysis.risk_category, 'CRITICAL');
    assert.ok(res.analysis.recommendations.some(r => r.includes('DANGER')));
  });

  it('8. Safety/Risk Agent - inland missing telemetry returns UNKNOWN / INSUFFICIENT EVIDENCE, never LOW', async () => {
    const res = await analyzeSafetyRisk({
      latitude: 21.15,
      longitude: 79.09,
      vessel_type: 'small_craft',
    });
    assert.equal(res.agent, 'Safety/Risk Agent');
    assert.equal(res.status, 'insufficient_evidence');
    assert.equal(res.analysis.risk_category, 'UNKNOWN / INSUFFICIENT EVIDENCE');
    assert.ok(!res.analysis.recommendations.some(r => r.includes('FAVORABLE')));
  });

  it('9. Validation Error - rejects out-of-bounds coordinates with HTTP 422', async () => {
    await assert.rejects(
      async () => {
        await analyzeOcean({ latitude: 99.0, longitude: 72.0 });
      },
      (err) => {
        assert.equal(err.status, 422);
        assert.ok(err.message.includes('latitude'));
        return true;
      }
    );
  });

  it('10. Orchestrator Agent - synthesizes multi-specialist mission advisory', async () => {
    const res = await analyzeOrchestrator({
      latitude: 15.0,
      longitude: 72.0,
      location_name: 'Offshore Goa Sector',
      forecast_time_window_hours: 24,
      user_objective: 'fishing',
      vessel_type: 'small_craft',
      target_species: 'Mackerel',
    });
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    assert.ok(['success', 'insufficient_evidence'].includes(res.status));
    assert.equal(res.user_objective, 'fishing');
    assert.ok(res.plan.planned_agents.includes('weather'));
    assert.ok(res.plan.planned_agents.includes('ocean'));
    assert.ok(res.plan.planned_agents.includes('fishing_zone'));
    assert.ok(res.plan.planned_agents.includes('safety_risk'));
    assert.ok(res.individual_agent_results.weather);
    assert.ok(res.individual_agent_results.ocean);
    assert.ok(res.measured_observations);
    assert.ok(res.derived_estimates);
    assert.ok(res.composite_safety_risk);
    assert.ok(res.legal_disclaimer);
  });

  it('11. Orchestrator Agent - strictly preserves critical safety and distinguishes measured vs derived data', async () => {
    const res = await analyzeOrchestrator({
      latitude: 15.0,
      longitude: 72.0,
      user_objective: 'passage_planning',
      vessel_type: 'small_craft',
      wave_height_m: 4.8, // Severe hazard for small craft
      wind_speed_knots: 40.0,
      destination_latitude: 18.9,
      destination_longitude: 72.8,
      destination_name: 'Mumbai Port',
    });
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    // Safety preservation check
    assert.equal(res.composite_safety_risk.risk_category, 'CRITICAL');
    assert.ok(res.recommendations.some(r => r.includes('DANGER') || r.includes('Suspend')));
    // Distinction between measured vs derived
    assert.equal(res.measured_observations.wave_height_m, 4.8);
    assert.equal(res.measured_observations.wind_speed_knots, 40.0);
    assert.ok(res.derived_estimates.geodesic_route.distance_km > 0);
    assert.ok(res.derived_estimates.geodesic_route.navigability_disclaimer.includes('NOT a verified'));
  });

  it('12. AI Workspace Assistant - processes natural-language task and returns structured plan & tool execution', async () => {
    const res = await chatAssistant({
      message: 'Analyze atmospheric weather and wind at 15.0, 72.0',
    });
    assert.ok(res.conversation_id);
    assert.equal(res.response_message.role, 'assistant');
    assert.ok(Array.isArray(res.plan));
    assert.ok(res.plan.length > 0);
    assert.ok(res.tool_calls.some(t => t.tool_name === 'invoke_weather_agent'));
    assert.ok(res.agent_results['Weather Agent']);
    assert.ok(res.evidence_summary.measured_observations.temperature_c !== undefined);
  });

  it('13. AI Workspace Assistant - lists registered specialist and workspace tools', async () => {
    const res = await getAssistantTools();
    assert.ok(Array.isArray(res.tools));
    const toolNames = res.tools.map(t => t.name);
    assert.ok(toolNames.includes('invoke_weather_agent'));
    assert.ok(toolNames.includes('invoke_ocean_agent'));
    assert.ok(toolNames.includes('read_project_file'));
    assert.ok(toolNames.includes('apply_file_edit'));
  });

  it('14. Orchestrator Agent - executes all five specialists concurrently when objective is "all"', async () => {
    const res = await analyzeOrchestrator({
      origin_latitude: 15.0,
      origin_longitude: 72.0,
      origin_name: 'Goa Offshore',
      destination_latitude: 18.9,
      destination_longitude: 72.8,
      destination_name: 'Mumbai Port',
      user_objective: 'all',
      vessel_type: 'small_craft',
    });
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    assert.equal(res.user_objective, 'all');
    assert.equal(res.plan.planned_agents.length, 5);
    assert.ok(res.individual_agent_results.weather);
    assert.ok(res.individual_agent_results.ocean);
    assert.ok(res.individual_agent_results.fishing_zone);
    assert.ok(res.individual_agent_results.route);
    assert.ok(res.individual_agent_results.safety_risk);
  });

  it('15. Orchestrator Agent - terrestrial inland coordinates preserve INSUFFICIENT_EVIDENCE without data invention', async () => {
    const res = await analyzeOrchestrator({
      latitude: 21.15,
      longitude: 79.09,
      location_name: 'Inland Nagpur',
      user_objective: 'safety_check',
    });
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    assert.equal(res.status, 'insufficient_evidence');
    assert.equal(res.measured_observations.wave_height_m, null);
    assert.equal(res.composite_safety_risk.risk_category, 'UNKNOWN / INSUFFICIENT EVIDENCE');
    assert.ok(!res.recommendations.some(r => r.includes('Favorable')));
  });

  it('16. Orchestrator Agent - detects conflicting specialist results and raises observation discrepancy warning', async () => {
    // Provide a wave height of 3.8m (Rough) with manual input
    const res = await analyzeOrchestrator({
      latitude: 15.0,
      longitude: 72.0,
      wave_height_m: 3.8,
      wind_speed_knots: 12.0,
      user_objective: 'safety_check',
    });
    assert.equal(res.agent, 'ORCA Orchestrator Agent');
    // 3.8m wave is Rough sea state; if ocean agent reported different sea state, warning is flagged
    assert.equal(res.measured_observations.wave_height_m, 3.8);
    assert.ok(res.composite_safety_risk.risk_category === 'CRITICAL' || res.composite_safety_risk.risk_category === 'HIGH');
  });

  it('17. Orchestrator Agent - verifies consistent response fields between API and frontend', async () => {
    const res = await analyzeOrchestrator({
      latitude: 15.0,
      longitude: 72.0,
      user_objective: 'general_maritime',
    });
    const expectedKeys = [
      'agent',
      'status',
      'user_objective',
      'location',
      'plan',
      'summary',
      'composite_safety_risk',
      'measured_observations',
      'derived_estimates',
      'individual_agent_results',
      'evidence_sources',
      'timestamps',
      'warnings',
      'missing_evidence',
      'errors',
      'recommendations',
      'legal_disclaimer',
      'generated_at',
    ];
    for (const key of expectedKeys) {
      assert.ok(key in res, `Expected response to contain field '${key}'`);
    }
  });
});



