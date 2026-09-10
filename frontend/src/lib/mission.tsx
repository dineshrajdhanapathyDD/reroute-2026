// Mission store: fetches a live plan from the backend, maps it into UI types,
// and exposes it app-wide. Falls back to bundled mock data when the backend is
// unavailable so the designed UI always renders.
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session, ScheduleBlock, Category, AgentActivityItem } from './types';
import type { JourneyLogEntry } from './types';
import { api, type BackendPlan } from './api';
import { mapSessions, mapScheduleBlocks, mapCategories, mapAgentActivity, mapJourneyLog, mapReroute } from './mappers';
import { MissionContext, type MissionState, type DroppedSession } from './missionContext';
import {
  sessions as mockSessions,
  categories as mockCategories,
  todayScheduleBlocks as mockSchedule,
  agentActivity as mockActivity,
  missionGoal as mockGoal,
} from './mockData';

export { useMission } from './missionContext';

const DEFAULT_MISSION =
  'Master production-ready AI agents on AWS — focus on Agents and Amazon Bedrock, arrive one day early.';

export function MissionProvider({ children }: { children: ReactNode }) {
  const [mission, setMission] = useState(DEFAULT_MISSION);
  const [goal, setGoal] = useState(mockGoal);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(false);
  const [journeyScore, setJourneyScore] = useState(82);
  const [routeQuality, setRouteQuality] = useState(86);
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [scheduleBlocks, setScheduleBlocks] = useState<ScheduleBlock[]>(mockSchedule);
  const [categories, setCategories] = useState<Category[]>(mockCategories);
  const [agentActivity, setAgentActivity] = useState<AgentActivityItem[]>(mockActivity);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [journeyLog, setJourneyLog] = useState<JourneyLogEntry[]>([]);
  const [droppedSessions, setDroppedSessions] = useState<DroppedSession[]>([]);

  const applyPlan = useCallback((p: BackendPlan) => {
    try {
      if (Array.isArray(p.sessions) && p.sessions.length) {
        setSessions(mapSessions(p.sessions));
        setSelectedIds(p.sessions.map((s) => s.id));
        setScheduleBlocks(mapScheduleBlocks(p));
      }
      const cats = mapCategories(p);
      if (cats.length) setCategories(cats);
      if (Array.isArray(p.agent_activity) && p.agent_activity.length) {
        setAgentActivity(mapAgentActivity(p.agent_activity));
      }
      setRecommendations(p.recommendations || []);
      setDroppedSessions(p.dropped_sessions || []);
      setJourneyLog(mapJourneyLog(p));
      if (p.trip?.learning_goal) setGoal(p.trip.learning_goal);
      if (p.scores?.journey_score != null) setJourneyScore(p.scores.journey_score);
      if (p.scores?.route_quality != null) setRouteQuality(p.scores.route_quality);
      setLive(true);
    } catch (err) {
      console.error('applyPlan mapping error (keeping fallback):', err);
    }
  }, []);

  const runPlan = useCallback(async (m?: string) => {
    const text = m ?? mission;
    setLoading(true);
    try {
      const plan = await api.createPlan(text);
      applyPlan(plan);
    } catch {
      setLive(false); // keep mock data
    } finally {
      setLoading(false);
    }
  }, [mission, applyPlan]);

  useEffect(() => { runPlan(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const reroute = useCallback(async (droppedId: string, reason = 'Session is full') => {
    try {
      const r = await api.reroute(droppedId, selectedIds, reason);
      return { options: mapReroute(r), recommendedId: r.recommended_alternative_id, metrics: r.metrics || [] };
    } catch {
      return { options: [], recommendedId: undefined, metrics: [] };
    }
  }, [selectedIds]);

  const acceptReroute = useCallback(async (droppedId: string, newSessionId: string) => {
    const nextIds = selectedIds.filter((id) => id !== droppedId).concat(newSessionId);
    try {
      const plan = await api.addSession(newSessionId, nextIds, goal);
      applyPlan(plan);
    } catch { /* keep current */ }
  }, [selectedIds, goal, applyPlan]);

  const value = useMemo<MissionState>(() => ({
    mission, goal, loading, live, journeyScore, routeQuality,
    sessions, scheduleBlocks, categories, agentActivity, journeyLog, droppedSessions,
    recommendations, selectedIds,
    setMission, runPlan, applyPlan, reroute, acceptReroute,
  }), [mission, goal, loading, live, journeyScore, routeQuality, sessions, scheduleBlocks,
    categories, agentActivity, journeyLog, droppedSessions, recommendations, selectedIds,
    runPlan, applyPlan, reroute, acceptReroute]);

  return <MissionContext.Provider value={value}>{children}</MissionContext.Provider>;
}
