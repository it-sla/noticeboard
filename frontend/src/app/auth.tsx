import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { api, ApiError, setCsrf } from "../lib/api";
import { ROLE_RANK, type Role, type Session, type User } from "../types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (min: Role) => boolean;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["session"],
    retry: false,
    staleTime: Infinity,
    queryFn: async () => {
      try {
        const s = await api.get<Session>("/auth/me");
        setCsrf(s.csrf_token);
        return s;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
  });
  const user = data?.user ?? null;
  const value: AuthValue = {
    user,
    loading: isLoading,
    can: (min) => !!user && ROLE_RANK[user.role] >= ROLE_RANK[min],
    login: async (email, password) => {
      const s = await api.post<Session>("/auth/login", { email, password });
      setCsrf(s.csrf_token);
      qc.setQueryData(["session"], s);
    },
    logout: async () => {
      await api.post("/auth/logout");
      setCsrf("");
      qc.clear();
      qc.setQueryData(["session"], null);
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
