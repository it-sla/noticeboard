import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router";
import { z } from "zod";
import { useAuth } from "../app/auth";
import { Button, Field, inputCls } from "../components/ui";
import { errorMessage } from "../lib/api";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type Form = z.infer<typeof schema>;

export function LoginPage() {
  const { user, login, can } = useAuth();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  if (user) return <Navigate to={can("ADMIN") ? "/dashboard" : "/notices"} replace />;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={handleSubmit(async (v) => {
          setError("");
          try {
            await login(v.email, v.password);
            nav("/", { replace: true });
          } catch (e) {
            setError(errorMessage(e));
          }
        })}
        className="w-full max-w-sm space-y-4 p-8 rounded-[18px] border border-hairline bg-white "
        noValidate
      >
        <div className="text-center">
          <img src="/logo.jpg" alt="Shangri La Tours" className="mx-auto mb-3 w-56" />
          <h1 className="text-base font-semibold text-brand-700">Employee Notice Board</h1>
          <p className="text-sm text-[#6e6e73]">Sign in to continue</p>
        </div>
        {error && (
          <p role="alert" className="rounded-[11px] bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <Field label="Email" error={errors.email?.message}>
          {(p) => <input {...p} type="email" autoComplete="username" className={inputCls} {...register("email")} />}
        </Field>
        <Field label="Password" error={errors.password?.message}>
          {(p) => <input {...p} type="password" autoComplete="current-password" className={inputCls} {...register("password")} />}
        </Field>
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
