"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Bot, Loader2, ArrowRight } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { apiClient } from "@/lib/api";
import type { User, AuthTokens } from "@/types";

interface AuthResponseData {
  user: User;
  tokens: AuthTokens;
}

const registerSchema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid work email"),
  organization_name: z.string().min(2, "Organization name must be at least 2 characters"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Include at least one uppercase letter")
    .regex(/\d/, "Include at least one number"),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { setAuth, loginAsDemo } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const res = await apiClient.post<AuthResponseData>("/auth/register", data);
      setAuth(res.data.user, res.data.tokens);
      toast.success("Workspace created! Welcome to SupportPilot AI.");
      router.push("/");
    } catch (err: any) {
      const message =
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        "Registration failed. Please check your details and try again.";
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-brand-50/40 to-blue-100/50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-tr from-brand-600 to-blue-500 rounded-2xl mb-4 shadow-xl shadow-brand-500/25">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">Create Workspace</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 font-medium">
            Start automating customer support with AI agents
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800/95 rounded-2xl shadow-xl border border-gray-200/80 dark:border-gray-700/80 p-8 backdrop-blur-sm">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
            {[
              { name: "full_name", label: "Full Name", type: "text", placeholder: "Alex Turner" },
              { name: "email", label: "Work Email", type: "email", placeholder: "alex@company.com" },
              { name: "organization_name", label: "Organization Name", type: "text", placeholder: "Acme Technologies" },
              { name: "password", label: "Password", type: "password", placeholder: "Min 8 chars, 1 uppercase, 1 digit" },
            ].map(({ name, label, type, placeholder }) => (
              <div key={name}>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  {label}
                </label>
                <input
                  {...register(name as keyof RegisterFormData)}
                  type={type}
                  placeholder={placeholder}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-700/50 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                />
                {errors[name as keyof RegisterFormData] && (
                  <p className="text-red-500 text-xs mt-1">
                    {errors[name as keyof RegisterFormData]?.message}
                  </p>
                )}
              </div>
            ))}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-semibold rounded-xl text-sm shadow-md shadow-brand-500/20 transition pt-3"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Start Free 14-Day Trial"}
            </button>
          </form>

          <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-brand-600 dark:text-brand-400 font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
