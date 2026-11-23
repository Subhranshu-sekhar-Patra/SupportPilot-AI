"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Bot, Eye, EyeOff, Loader2, Sparkles, ArrowRight } from "lucide-react";
import { useAuthStore } from "@/store/auth";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid work email"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { setAuth, loginAsDemo } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "alex.turner@supportpilot.io",
      password: "Password123!",
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    // Phase 2 realistic client login simulation
    await new Promise((r) => setTimeout(r, 600));
    loginAsDemo();
    toast.success("Welcome back, Alex Turner!");
    router.push("/");
  };

  const handleQuickDemo = () => {
    setValue("email", "alex.turner@supportpilot.io");
    setValue("password", "Password123!");
    loginAsDemo();
    toast.success("Logged in with Demo Admin credentials!");
    router.push("/");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-brand-50/40 to-blue-100/50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 p-4">
      <div className="w-full max-w-md">
        {/* Brand Logo & Headline */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-tr from-brand-600 to-blue-500 rounded-2xl mb-4 shadow-xl shadow-brand-500/25">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">SupportPilot AI</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 font-medium">
            Intelligent Customer Support Automation Platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-gray-800/95 rounded-2xl shadow-xl border border-gray-200/80 dark:border-gray-700/80 p-8 backdrop-blur-sm">
          {/* 1-Click Demo Access Banner */}
          <div className="mb-6 p-3 rounded-xl bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-950/60 dark:to-purple-950/60 border border-brand-200/60 dark:border-brand-800/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" />
              <div>
                <p className="text-xs font-bold text-gray-900 dark:text-white">Instant Demo Access</p>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">Preloaded with mock enterprise data</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleQuickDemo}
              className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1 transition"
            >
              Demo <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                Work Email Address
              </label>
              <input
                {...register("email")}
                type="email"
                autoComplete="email"
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/50 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                  Password
                </label>
                <a href="#" className="text-xs text-brand-600 dark:text-brand-400 hover:underline">
                  Forgot?
                </a>
              </div>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/50 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-semibold rounded-xl text-sm shadow-md shadow-brand-500/20 transition mt-2"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in to Workspace"}
            </button>
          </form>

          <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
            Need a new workspace?{" "}
            <Link href="/register" className="text-brand-600 dark:text-brand-400 font-semibold hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
