import React, { useState, useEffect } from "react";
import { api } from "./utils/api";
import { playSound } from "./utils/audio";
import ChatConsole from "./components/ChatConsole";
import TaskBoard from "./components/TaskBoard";
import StudyCalendar from "./components/StudyCalendar";
import Flashcards from "./components/Flashcards";
import AuditLogs from "./components/AuditLogs";
import { 
  Terminal, 
  ListTodo, 
  Calendar, 
  HelpCircle, 
  Layers, 
  Cpu, 
  LogOut, 
  Maximize2, 
  Minimize2, 
  X, 
  Lock,
  Sparkles,
  Settings,
  Flame
} from "lucide-react";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.isLoggedIn());
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  
  // Data States
  const [tasks, setTasks] = useState([]);
  const [events, setEvents] = useState([]);
  const [flashcards, setFlashcards] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [streakCount, setStreakCount] = useState(0);
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  // Window Manager States
  const [windows, setWindows] = useState({
    missionControl: true,
    ledger: true,
    timeGrid: true,
    memoryVault: true,
    auditLogs: false,
  });

  const [maximizedWindow, setMaximizedWindow] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedPlannerModel, setSelectedPlannerModel] = useState("llama3.2 (3B)");
  const [selectedSubagentModel, setSelectedSubagentModel] = useState("qwen2.5 (1.5B)");

  // Real-time ticking clock
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Listen to auth changes
  useEffect(() => {
    const handleAuthChange = () => setLoggedIn(api.isLoggedIn());
    window.addEventListener("auth-change", handleAuthChange);
    return () => window.removeEventListener("auth-change", handleAuthChange);
  }, []);

  // Fetch all backend data
  const refreshData = async () => {
    if (!loggedIn) return;
    try {
      const [tasksData, eventsData, cardsData, logsData, streakData] = await Promise.all([
        api.getTasks(),
        api.getCalendar(),
        api.getDueFlashcards(),
        api.getAuditLogs(),
        api.getVaultStreak()
      ]);
      setTasks(tasksData);
      setEvents(eventsData);
      setFlashcards(cardsData);
      setAuditLogs(logsData);
      setStreakCount(streakData?.current_streak || 0);
    } catch (err) {
      console.error("Data refresh failed", err);
    }
  };

  useEffect(() => {
    if (loggedIn) {
      refreshData();
    }
  }, [loggedIn]);

  const handleLogin = async (e) => {
    e.preventDefault();
    playSound.click();
    setLoginError("");
    setSuccessMsg("");
    try {
      await api.login(username, password);
      playSound.success();
    } catch (err) {
      playSound.error();
      setLoginError(err.message || "Login failed");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    playSound.click();
    setLoginError("");
    setSuccessMsg("");
    try {
      await api.register(username, password);
      playSound.success();
      setSuccessMsg("REGISTRATION SUCCESSFUL! YOU CAN NOW LOG IN.");
      setIsRegistering(false);
    } catch (err) {
      playSound.error();
      setLoginError(err.message || "Registration failed");
    }
  };

  const handleLogout = () => {
    playSound.click();
    api.logout();
  };

  const toggleWindow = (name) => {
    playSound.click();
    setWindows((prev) => ({ ...prev, [name]: !prev[name] }));
    if (maximizedWindow === name) {
      setMaximizedWindow(null);
    }
  };

  const toggleMaximize = (name) => {
    playSound.click();
    if (maximizedWindow === name) {
      setMaximizedWindow(null);
    } else {
      setMaximizedWindow(name);
    }
  };

  // Render Login Screen
  if (!loggedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#8B5CF6] p-4 crt-screen font-retro-terminal relative overflow-hidden">
        
        {/* Glowing Matrix Grid Background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#000000_1px,transparent_1px),linear-gradient(to_bottom,#000000_1px,transparent_1px)] bg-[size:3rem_3rem] opacity-20"></div>
        <div className="absolute top-[-20%] left-[-20%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,rgba(0,0,0,0.1)_0%,transparent_60%)] pointer-events-none"></div>

        {/* ASCII Logo Header */}
        <div className="text-center z-10 mb-6 select-none animate-pulse">
          <pre className="text-[#FFDE4D] text-[8px] sm:text-xs leading-none font-bold drop-shadow-[0_0_4px_#FFDE4D] whitespace-pre">
{`   _____  __  __ _  _    __   ____  ____  ____ 
  / ___/ /  \\/  ( \\/ )  / _\\ (  _ \\/ ___)(  __)
  \\___ \\(  O  O )  /  /    \\ ) __/\\___ \\ ) _) 
  /____/ \\__/__/\\_/   \\_/\\_/(__)  (____/(____)`}
          </pre>
          <div className="text-[#FF006E] text-xs font-bold tracking-widest mt-2 uppercase drop-shadow-[0_0_4px_rgba(255,0,110,0.5)]">
            // LOCAL MULTI-AGENT HANDOFF CONSOLE v1.0
          </div>
        </div>

        {/* Console Login Box */}
        <div className="w-full max-w-md border-4 border-black bg-[#FFF5F5] neo-shadow drop-shadow-[0_0_15px_rgba(0,0,0,0.15)] p-6 z-10 relative">
          
          {/* Header Title */}
          <div className="absolute top-0 right-0 left-0 bg-black text-[#FFF5F5] font-bold p-2 text-center text-xs flex items-center justify-center gap-1.5 border-b-4 border-black">
            <Lock className="h-3.5 w-3.5" />
            {isRegistering ? "OPERATOR REGISTRATION PORTAL" : "SECURE ACCESS PORTAL // ACCESS CODE REQUIRED"}
          </div>
          
          <form onSubmit={isRegistering ? handleRegister : handleLogin} className="mt-6 space-y-5">
            {loginError && (
              <div className="border-2 border-black bg-[#FF006E] p-2.5 text-[#FFF5F5] text-xs font-bold text-center border-dashed animate-bounce">
                !!! SYSTEM_ALERT: {loginError.toUpperCase()} !!!
              </div>
            )}

            {successMsg && (
              <div className="border-2 border-black bg-[#FFF5F5] p-2.5 text-black text-xs font-bold text-center border-dashed">
                *** SUCCESS: {successMsg} ***
              </div>
            )}
            
            {/* System Boot simulation */}
            <div className="text-[10px] text-[#00F5D4] text-opacity-80 space-y-0.5 font-mono border border-black p-2 bg-black">
              <div>&gt; HOST MACHINE CONNECTED: INTEL ULTRA 9 [OK]</div>
              <div>&gt; SQLITE INTERFACE SEEDED: SYNAPSE.DB [OK]</div>
              <div>&gt; OLLAMA ROUTER PORT 11434 LISTEN: READY [OK]</div>
            </div>

            <div>
              <label className="block text-xs text-black font-bold mb-1">
                {isRegistering ? "operator@synapse:~$ create-id" : "operator@synapse:~$ enter-id"}
              </label>
              <div className="relative">
                <span className="absolute left-2.5 top-2 text-black">&gt;</span>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black text-black pl-6 pr-3 py-2 text-sm focus:outline-none focus:border-black focus:ring-1 focus:ring-black font-bold font-mono tracking-wide placeholder-black placeholder-opacity-40"
                  placeholder={isRegistering ? "newusername" : "admin"}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-black font-bold mb-1">
                {isRegistering ? "operator@synapse:~$ create-passcode" : "operator@synapse:~$ enter-passcode"}
              </label>
              <div className="relative">
                <span className="absolute left-2.5 top-2 text-black">&gt;</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black text-black pl-6 pr-3 py-2 text-sm focus:outline-none focus:border-black focus:ring-1 focus:ring-black font-bold font-mono tracking-wide placeholder-black placeholder-opacity-40"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full border-4 border-black bg-[#FF006E] text-[#FFF5F5] hover:bg-[#FFDE4D] hover:text-black transition-all py-2.5 text-xs font-bold mt-2 hover:shadow-[0_0_10px_rgba(0,0,0,0.15)] uppercase tracking-widest active:translate-y-1"
            >
              {isRegistering ? "[ REGISTER NEW OPERATOR IDENTITY ]" : "[ INITIALIZE ACCESS SEQUENCE ]"}
            </button>

            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={() => {
                  playSound.click();
                  setIsRegistering(!isRegistering);
                  setLoginError("");
                  setSuccessMsg("");
                }}
                className="text-xs text-black hover:text-[#FF006E] underline font-bold"
              >
                {isRegistering ? "[ RETURN TO LOGIN SEQUENCING ]" : "[ CREATE NEW OPERATOR IDENTITY ]"}
              </button>
            </div>
            
            <div className="text-[9px] text-black text-opacity-60 text-center pt-1 border-t border-black border-opacity-10">
              SECURE ACCESS BLOCK // JWT AES-256 SIGNATURE AUTH
            </div>
          </form>
        </div>
      </div>
    );
  }

  // Window title bar helper
  const WindowHeader = ({ title, name, color = "bg-[#000000] text-[#FFF5F5]" }) => (
    <div className={`neo-border-b border-b-4 border-black p-1.5 flex justify-between items-center ${color} font-bold text-xs`}>
      <span className="flex items-center gap-1">
        <span>[{name.toUpperCase()}.EXE]</span>
        <span>— {title}</span>
      </span>
      <div className="flex gap-2">
        <button 
          onClick={() => toggleMaximize(name)}
          className="p-0.5 neo-border bg-[#FFF5F5] text-black hover:bg-[#00F5D4]"
          title="Maximize"
        >
          {maximizedWindow === name ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
        </button>
        <button 
          onClick={() => toggleWindow(name)}
          className="p-0.5 neo-border bg-[#FF006E] text-[#FFF5F5] hover:bg-black hover:text-[#FF006E]"
          title="Close"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#8B5CF6] flex flex-col font-retro-terminal select-none">
      
      {/* 1. System Bar Header */}
      <header className="neo-border border-b-4 bg-black text-[#FFF5F5] p-2 flex flex-wrap justify-between items-center z-30">
        <div className="flex items-center gap-4">
          <div className="bg-[#FFDE4D] text-black px-2 py-1 font-bold text-sm neo-border flex items-center gap-1.5 animate-pulse">
            <Cpu className="h-4 w-4" />
            SYNAPSE OS V1.0
          </div>
          
          {/* Active status lights */}
          <div className="hidden lg:flex items-center gap-3 text-[10px] font-bold">
            <span className="flex items-center gap-1.5 text-[#FFF5F5]">
              <span className="h-2 w-2 rounded-full bg-[#00F5D4] animate-ping" />
              PLANNER: ACTIVE
            </span>
            <span className="flex items-center gap-1.5 text-[#FFF5F5]">
              <span className="h-2 w-2 rounded-full bg-[#FFDE4D]" />
              OPTIMIZER: STANDBY
            </span>
            <span className="flex items-center gap-1.5 text-[#FFF5F5]">
              <span className="h-2 w-2 rounded-full bg-[#FF006E]" />
              STUDY: ON_CALL
            </span>
            <span className="flex items-center gap-1.5 text-[#FFF5F5] text-opacity-50">
              <span className="h-2 w-2 rounded-full bg-[#FFF5F5] bg-opacity-50" />
              SCHEDULER: IDLE
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-xs hidden sm:inline text-[#FFF5F5]">{time}</span>
          
          {/* Settings Trigger */}
          <button 
            onClick={() => { playSound.click(); setShowSettings(!showSettings); }}
            className="neo-btn bg-[#FFF5F5] text-black px-2 py-1 text-xs flex items-center gap-1 hover:bg-[#00F5D4]"
          >
            <Settings className="h-4 w-4" />
            SETTINGS
          </button>

          {/* Logout */}
          <button 
            onClick={handleLogout}
            className="neo-btn bg-[#FF006E] text-[#FFF5F5] px-2 py-1 text-xs flex items-center gap-1 hover:bg-[#000000] hover:text-[#FF006E]"
          >
            <LogOut className="h-4 w-4" />
            SHUTDOWN
          </button>
        </div>
      </header>

      {/* 2. Model Settings Panel Overlay */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
          <div className="neo-border bg-[#FFF5F5] text-black neo-shadow max-w-md w-full p-4 relative">
            <button 
              onClick={() => { playSound.click(); setShowSettings(false); }}
              className="absolute top-2 right-2 neo-border bg-[#FF006E] text-[#FFF5F5] hover:bg-black hover:text-[#FF006E] p-1"
            >
              <X className="h-4 w-4" />
            </button>
            <h3 className="font-bold text-sm border-b-4 border-black pb-2 mb-4">SYSTEM MODEL CONFIGURATION</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold mb-1">PLANNER/ROOT AGENT MODEL (LOCAL OLLAMA)</label>
                <select 
                  value={selectedPlannerModel}
                  onChange={(e) => { playSound.click(); setSelectedPlannerModel(e.target.value); }}
                  className="w-full neo-border px-2 py-1.5 text-xs font-bold bg-[#FFF5F5] text-black"
                >
                  <option value="llama3.2 (3B)">llama3.2:latest (3B) [Fast CPU]</option>
                  <option value="llama3.1 (8B)">llama3.1:8b (8B) [High Intelligence]</option>
                  <option value="qwen2.5 (3B)">qwen2.5:3b (3B)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold mb-1">SUB-AGENTS CORE MODEL (OPTIMIZER/STUDY/SCHEDULER)</label>
                <select 
                  value={selectedSubagentModel}
                  onChange={(e) => { playSound.click(); setSelectedSubagentModel(e.target.value); }}
                  className="w-full neo-border px-2 py-1.5 text-xs font-bold bg-[#FFF5F5] text-black"
                >
                  <option value="qwen2.5 (1.5B)">qwen2.5:1.5b (1.5B) [Instant CPU]</option>
                  <option value="llama3.2 (1B)">llama3.2:1b (1B) [Ultra Light]</option>
                  <option value="qwen2.5 (7B)">qwen2.5:7b (7B)</option>
                </select>
              </div>

              <div className="bg-[#FFDE4D] bg-opacity-20 border-2 border-black p-3 text-[11px] text-black leading-relaxed font-bold">
                * Note: Model selection modifies API mappings. Ensure appropriate models have been pulled via:
                <code className="block bg-black text-[#FFF5F5] p-1 mt-1 font-mono text-[10px] border border-black">
                  ollama pull &lt;model-name&gt;
                </code>
              </div>
            </div>

            <button
              onClick={() => { playSound.success(); setShowSettings(false); }}
              className="w-full neo-btn bg-[#FFDE4D] text-black py-2 mt-4 text-xs font-bold hover:bg-black hover:text-[#FFDE4D]"
            >
              SAVE CONFIGURATION
            </button>
          </div>
        </div>
      )}

      {/* 3. Main Workspace Area */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Shortcut Left Bar */}
        <aside className="w-16 md:w-20 neo-border border-r-4 bg-[#FFF5F5] flex flex-col items-center py-4 gap-4 z-10 shrink-0">
          <button
            onClick={() => toggleWindow("missionControl")}
            className={`p-2 neo-border flex flex-col items-center gap-1 text-[9px] font-bold ${
              windows.missionControl ? "bg-[#FFDE4D] text-black" : "bg-[#FFF5F5] text-black border-opacity-50"
            } hover:bg-[#FF006E] hover:text-[#FFF5F5] w-12 md:w-14 h-12 md:h-14 justify-center`}
          >
            <Terminal className="h-4 w-4" />
            <span>CHAT</span>
          </button>

          <button
            onClick={() => toggleWindow("ledger")}
            className={`p-2 neo-border flex flex-col items-center gap-1 text-[9px] font-bold ${
              windows.ledger ? "bg-[#FFDE4D] text-black" : "bg-[#FFF5F5] text-black border-opacity-50"
            } hover:bg-[#FF006E] hover:text-[#FFF5F5] w-12 md:w-14 h-12 md:h-14 justify-center`}
          >
            <ListTodo className="h-4 w-4" />
            <span>TASKS</span>
          </button>

          <button
            onClick={() => toggleWindow("timeGrid")}
            className={`p-2 neo-border flex flex-col items-center gap-1 text-[9px] font-bold ${
              windows.timeGrid ? "bg-[#FFDE4D] text-black" : "bg-[#FFF5F5] text-black border-opacity-50"
            } hover:bg-[#FF006E] hover:text-[#FFF5F5] w-12 md:w-14 h-12 md:h-14 justify-center`}
          >
            <Calendar className="h-4 w-4" />
            <span>TIME</span>
          </button>

          <button
            onClick={() => toggleWindow("memoryVault")}
            className={`p-2 neo-border flex flex-col items-center gap-1 text-[9px] font-bold relative ${
              windows.memoryVault ? "bg-[#FFDE4D] text-black" : "bg-[#FFF5F5] text-black border-opacity-50"
            } hover:bg-[#FF006E] hover:text-[#FFF5F5] w-12 md:w-14 h-12 md:h-14 justify-center`}
          >
            <Sparkles className="h-4 w-4" />
            <span>VAULT</span>
            {flashcards.length > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-[#FF006E] text-[#FFF5F5] border-2 border-black rounded-full text-[8px] h-5 w-5 flex items-center justify-center font-bold">
                {flashcards.length}
              </span>
            )}
            {streakCount > 0 && (
              <span className="absolute -bottom-1.5 -left-1.5 bg-[#FFDE4D] text-black border-2 border-black rounded-none text-[8px] h-5 px-1 flex items-center justify-center font-bold gap-0.5 shadow-[1px_1px_0px_#000]" title={`${streakCount} day review streak!`}>
                <Flame className="h-3 w-3 fill-current text-[#FF006E]" />
                {streakCount}
              </span>
            )}
          </button>

          <button
            onClick={() => toggleWindow("auditLogs")}
            className={`p-2 neo-border flex flex-col items-center gap-1 text-[9px] font-bold ${
              windows.auditLogs ? "bg-[#FFDE4D] text-black" : "bg-[#FFF5F5] text-black border-opacity-50"
            } hover:bg-[#FF006E] hover:text-[#FFF5F5] w-12 md:w-14 h-12 md:h-14 justify-center`}
          >
            <Cpu className="h-4 w-4" />
            <span>LOGS</span>
          </button>
        </aside>

        {/* Floating Tiled Workspace Panel */}
        <main className="flex-1 p-4 overflow-y-auto bg-[#8B5CF6] relative">
          
          {maximizedWindow ? (
            // Full Screen Maximized Window Mode
            <div className="neo-border bg-[#FFF5F5] neo-shadow h-full flex flex-col">
              <WindowHeader 
                title={
                  maximizedWindow === "missionControl" ? "MISSION_CONTROL (Root Planner)" :
                  maximizedWindow === "ledger" ? "THE_LEDGER (Eisenhower Task Board)" :
                  maximizedWindow === "timeGrid" ? "TIME_GRID (Calendar Scheduler)" :
                  maximizedWindow === "memoryVault" ? "MEMORY_VAULT (Spaced Repetition Review)" :
                  "SYSTEM_AUDIT_LOGS"
                }
                name={maximizedWindow}
                color={
                  maximizedWindow === "missionControl" ? "bg-[#FF006E] text-[#FFF5F5]" :
                  maximizedWindow === "ledger" ? "bg-[#FFDE4D] text-black" :
                  maximizedWindow === "timeGrid" ? "bg-[#00F5D4] text-black" :
                  maximizedWindow === "memoryVault" ? "bg-[#8B5CF6] text-[#FFF5F5]" :
                  "bg-black text-[#FFF5F5]"
                }
              />
              <div className="flex-1 overflow-hidden p-2">
                {maximizedWindow === "missionControl" && <ChatConsole onPipelineComplete={refreshData} />}
                {maximizedWindow === "ledger" && <TaskBoard tasks={tasks} onRefresh={refreshData} />}
                {maximizedWindow === "timeGrid" && <StudyCalendar events={events} onRefresh={refreshData} />}
                {maximizedWindow === "memoryVault" && <Flashcards cards={flashcards} onRefresh={refreshData} />}
                {maximizedWindow === "auditLogs" && <AuditLogs logs={auditLogs} onRefresh={refreshData} />}
              </div>
            </div>
          ) : (
            // Standard Multi-Window Tiled Workspace Mode
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-12">
              
              {/* 1. Mission Control */}
              {windows.missionControl && (
                <div className="neo-border bg-[#FFF5F5] neo-shadow flex flex-col h-full min-h-[350px]">
                  <WindowHeader title="MISSION_CONTROL (Root Planner)" name="missionControl" color="bg-[#FF006E] text-[#FFF5F5]" />
                  <div className="flex-1 p-1 overflow-hidden">
                    <ChatConsole onPipelineComplete={refreshData} />
                  </div>
                </div>
              )}

              {/* 2. Ledger Task Board */}
              {windows.ledger && (
                <div className="neo-border bg-[#FFF5F5] neo-shadow flex flex-col h-full min-h-[350px]">
                  <WindowHeader title="THE_LEDGER (Eisenhower Task Board)" name="ledger" color="bg-[#FFDE4D] text-black" />
                  <div className="flex-1 p-2 overflow-y-auto">
                    <TaskBoard tasks={tasks} onRefresh={refreshData} />
                  </div>
                </div>
              )}

              {/* 3. Time Grid */}
              {windows.timeGrid && (
                <div className="neo-border bg-[#FFF5F5] neo-shadow flex flex-col h-[450px] min-h-[350px]">
                  <WindowHeader title="TIME_GRID (Calendar Scheduler)" name="timeGrid" color="bg-[#00F5D4] text-black" />
                  <div className="flex-1 p-2 overflow-y-scroll">
                    <StudyCalendar events={events} onRefresh={refreshData} />
                  </div>
                </div>
              )}

              {/* 4. Memory Vault */}
              {windows.memoryVault && (
                <div className="neo-border bg-[#FFF5F5] neo-shadow flex flex-col h-[450px] min-h-[350px]">
                  <WindowHeader title="MEMORY_VAULT (Spaced Repetition Review)" name="memoryVault" color="bg-[#8B5CF6] text-[#FFF5F5]" />
                  <div className="flex-1 p-2 overflow-y-scroll">
                    <Flashcards cards={flashcards} onRefresh={refreshData} />
                  </div>
                </div>
              )}

              {/* 5. System Logs */}
              {windows.auditLogs && (
                <div className="neo-border bg-[#FFF5F5] neo-shadow flex flex-col h-full min-h-[350px] xl:col-span-2">
                  <WindowHeader title="SYSTEM_AUDIT_LOGS (Integrity Audit)" name="auditLogs" color="bg-black text-[#FFF5F5]" />
                  <div className="flex-1 p-2 overflow-y-auto">
                    <AuditLogs logs={auditLogs} onRefresh={refreshData} />
                  </div>
                </div>
              )}

            </div>
          )}

        </main>
      </div>

      {/* Footer bar */}
      <footer className="neo-border border-t-4 bg-black text-[#FFF5F5] text-[10px] p-1.5 flex justify-between z-10 shrink-0">
        <span>MEM: 32GB // CPU: INTEL ULTRA 9 185H</span>
        <span>SECURE HANDOFF MATRIX ACTIVE // 100% LOCAL EXECUTION</span>
      </footer>

    </div>
  );
}
