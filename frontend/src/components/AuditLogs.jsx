import React from "react";
import { playSound } from "../utils/audio";
import { api } from "../utils/api";
import { RefreshCw, ShieldAlert, Cpu } from "lucide-react";

export default function AuditLogs({ logs, onRefresh }) {
  return (
    <div className="flex flex-col h-full bg-[#FFF5F5] text-black p-3 font-retro-terminal crt-screen">
      {/* Top Header */}
      <div className="flex justify-between items-center pb-2 border-b-2 border-black mb-3">
        <div className="flex items-center gap-1.5 text-xs font-bold">
          <Cpu className="h-4 w-4" />
          <span>SYNAPSE AUDIT LOGS (INTEGRITY COMPLIANCE)</span>
        </div>
        <button
          onClick={() => { playSound.click(); onRefresh(); }}
          className="neo-btn bg-[#FFDE4D] text-black border-2 border-black px-2 py-0.5 text-[10px] flex items-center gap-1 hover:bg-black hover:text-[#FFDE4D]"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          REFRESH
        </button>
      </div>

      {/* Logs Scroll container */}
      <div className="flex-1 overflow-y-auto space-y-2 max-h-[300px] text-[11px] leading-relaxed bg-[#FFF5F5] p-2 border border-black">
        {logs.length === 0 ? (
          <div className="text-center text-black text-opacity-60 py-8 italic font-bold">
            NO AUDIT LOGS RECORDED
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className={`p-2 border-b border-black border-opacity-25 transition-all ${
                log.status === "error" ? "bg-black text-[#FFDE4D]" : "text-black"
              }`}
            >
              <div className="flex justify-between items-center font-bold">
                <span>
                  [{new Date(log.timestamp).toLocaleTimeString()}] AGENT: {log.agent_name}
                </span>
                <span className={`px-1 text-[9px] font-bold border ${
                  log.status === "success" 
                    ? "bg-[#00F5D4] text-black border-black" 
                    : "bg-black text-[#FFDE4D] border-black"
                }`}>
                  {log.status.toUpperCase()}
                </span>
              </div>
              <div className="mt-1">
                <span className="font-bold">TOOL:</span> {log.tool_name}
              </div>
              {log.parameters && (
                <div className="mt-1 text-opacity-80 overflow-x-auto whitespace-pre-wrap">
                  <span className="font-bold">PARAMS:</span> {log.parameters}
                </div>
              )}
              {log.error && (
                <div className="mt-1 font-bold flex items-center gap-1">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  <span>ERROR: {log.error}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
