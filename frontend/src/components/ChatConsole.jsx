import React, { useState } from "react";
import { api } from "../utils/api";
import { playSound } from "../utils/audio";
import { Terminal, Send, Cpu, CheckCircle, Upload } from "lucide-react";

export default function ChatConsole({ onPipelineComplete }) {
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [output, setOutput] = useState("");

  const handleRunGoal = async (e) => {
    e.preventDefault();
    if (!goal.trim()) return;

    playSound.click();
    setLoading(true);
    setLogs(["[SYSTEM] Initializing multi-agent pipeline...", "[SYSTEM] Activating Planner Agent..."]);
    setOutput("");

    try {
      const data = await api.runAgentGoal(goal);
      
      if (data.status === "success") {
        setLogs((prev) => [...prev, ...data.logs, "[SYSTEM] Pipeline executed successfully."]);
        setOutput(
          `PLAN SYNTHESIS:\n` +
          `===================================\n` +
          `Tasks Created: ${data.tasks_created.length}\n` +
          `Flashcards Generated: ${data.flashcards_created.length}\n` +
          `Schedule Events Booked: ${data.calendar_events_created.length}\n\n` +
          `All events and tasks have been written to the ledger & calendar.`
        );
        playSound.success();
        if (onPipelineComplete) onPipelineComplete();
      } else {
        throw new Error(data.message || "Execution failed");
      }
    } catch (err) {
      playSound.error();
      setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    playSound.click();
    setLoading(true);
    setLogs([
      `[SYSTEM] Uploading file: ${file.name}`,
      `[SYSTEM] Reading file content and extracting text (PDF pages)...`,
      `[SYSTEM] Activating Planner Agent with file content...`
    ]);
    setOutput("");

    try {
      const data = await api.uploadFilePipeline(file);
      
      if (data.status === "success" || data.pipeline_result?.status === "success") {
        const pipelineResult = data.pipeline_result || data;
        const tasksLength = pipelineResult.tasks_created?.length || 0;
        const flashcardsLength = pipelineResult.flashcards_created?.length || 0;
        const calendarLength = pipelineResult.calendar_events_created?.length || 0;
        const executionLogs = pipelineResult.logs || [];

        setLogs((prev) => [
          ...prev, 
          ...executionLogs, 
          `[SYSTEM] File text extracted successfully (${data.extracted_length || 0} characters).`,
          "[SYSTEM] Pipeline executed successfully."
        ]);
        
        setOutput(
          `FILE PLAN SYNTHESIS [${data.filename}]:\n` +
          `===================================\n` +
          `Tasks Created: ${tasksLength}\n` +
          `Flashcards Generated: ${flashcardsLength}\n` +
          `Schedule Events Booked: ${calendarLength}\n\n` +
          `All events and tasks have been written to the ledger & calendar.`
        );
        playSound.success();
        if (onPipelineComplete) onPipelineComplete();
      } else {
        throw new Error(data.message || "File pipeline execution failed");
      }
    } catch (err) {
      playSound.error();
      setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#FFF5F5] text-black p-4 font-retro-terminal crt-screen">
      <div className="flex-1 overflow-y-auto space-y-3 border-2 border-black p-3 bg-[#FFF5F5] min-h-[220px]">
        <div className="text-xs text-opacity-70 text-black">
          SYSTEM ACTIVE // OLLAMA BACKEND AT PORT 11434
        </div>
        
        {logs.map((log, index) => (
          <div key={index} className="text-sm leading-relaxed whitespace-pre-wrap font-bold">
            {log}
          </div>
        ))}

        {output && (
          <div className="mt-4 p-3 border border-black text-black text-sm bg-[#FFDE4D] whitespace-pre-wrap font-bold">
            {output}
          </div>
        )}
      </div>

      <form onSubmit={handleRunGoal} className="mt-4 flex gap-2">
        <div className="relative flex-1">
          <Terminal className="absolute left-3 top-3 h-5 w-5 text-black" />
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            disabled={loading}
            placeholder="ENTER STUDY/SCHEDULING GOAL..."
            className="w-full bg-[#FFF5F5] border-2 border-black pl-10 pr-4 py-2 text-black placeholder-black placeholder-opacity-50 focus:outline-none focus:border-[#FF006E] font-bold"
          />
        </div>

        <input
          type="file"
          id="chat-file-upload"
          accept=".pdf,.txt,.md,.json"
          onChange={handleFileUpload}
          disabled={loading}
          className="hidden"
        />

        <label
          htmlFor="chat-file-upload"
          className={`neo-btn bg-[#00F5D4] text-black px-4 py-2 flex items-center gap-2 hover:bg-black hover:text-[#00F5D4] cursor-pointer font-bold border-2 border-black select-none ${
            loading ? "opacity-50 pointer-events-none" : ""
          }`}
          title="Upload PDF or text file to plan"
        >
          <Upload className="h-5 w-5" />
          FILE
        </label>

        <button
          type="submit"
          disabled={loading}
          className="neo-btn bg-[#FFDE4D] text-black px-4 py-2 flex items-center gap-2 hover:bg-black hover:text-[#FFDE4D] disabled:bg-[#FFF5F5] disabled:text-black disabled:opacity-50 disabled:transform-none"
        >
          {loading ? (
            <>
              <Cpu className="animate-spin h-5 w-5" />
              RUNNING...
            </>
          ) : (
            <>
              <Send className="h-5 w-5" />
              EXECUTE
            </>
          )}
        </button>
      </form>
    </div>
  );
}
