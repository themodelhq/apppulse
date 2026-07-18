"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { wsUrl } from "./api";

/**
 * Subscribes to the backend's /ws broadcast channel. Whenever the scheduler
 * finishes a refresh cycle, it pushes a message here and we invalidate the
 * relevant React Query caches so the dashboard updates live instead of
 * waiting on the next poll.
 */
export function useLiveUpdates() {
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const retryRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket;
    let closedByUs = false;

    function connect() {
      socket = new WebSocket(wsUrl());

      socket.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "refresh") {
            setLastUpdate(payload.at);
            queryClient.invalidateQueries({ queryKey: ["kpis"] });
            queryClient.invalidateQueries({ queryKey: ["apps"] });
            queryClient.invalidateQueries({ queryKey: ["alerts"] });
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (!closedByUs) {
          const delay = Math.min(30_000, 1000 * 2 ** retryRef.current);
          retryRef.current += 1;
          setTimeout(connect, delay);
        }
      };
    }

    connect();
    return () => {
      closedByUs = true;
      socket?.close();
    };
  }, [queryClient]);

  return { connected, lastUpdate };
}
