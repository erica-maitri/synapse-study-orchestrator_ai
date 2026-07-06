import React from "react";
import { playSound } from "../utils/audio";
import { api } from "../utils/api";
import { CheckCircle2, Circle, Trash2, Award } from "lucide-react";

export default function TaskBoard({ tasks, onRefresh }) {
  const quadrants = [
    { id: "Q1: Do First", title: "Q1: DO FIRST", color: "bg-[#FF006E] text-[#FFF5F5]" },
    { id: "Q2: Schedule", title: "Q2: SCHEDULE", color: "bg-[#FFDE4D] text-[#000000]" },
    { id: "Q3: Delegate/Optimize", title: "Q3: DELEGATE/OPTIMIZE", color: "bg-[#00F5D4] text-[#000000]" },
    { id: "Q4: Eliminate", title: "Q4: ELIMINATE", color: "bg-[#8B5CF6] text-[#FFF5F5] opacity-60" }
  ];

  const handleToggleComplete = async (task) => {
    playSound.click();
    const newStatus = task.status === "completed" ? "pending" : "completed";
    try {
      await api.updateTask(task.id, { status: newStatus });
      if (newStatus === "completed") {
        playSound.success();
      }
      onRefresh();
    } catch (err) {
      playSound.error();
    }
  };

  const handleDelete = async (id) => {
    playSound.click();
    if (confirm("Are you sure you want to delete this task?")) {
      try {
        await api.deleteTask(id);
        playSound.success();
        onRefresh();
      } catch (err) {
        playSound.error();
      }
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full overflow-y-auto p-2 bg-[#FFF5F5]">
      {quadrants.map((q) => {
        const qTasks = tasks.filter((t) => t.quadrant === q.id);
        
        return (
          <div key={q.id} className="neo-border bg-[#FFF5F5] flex flex-col h-[300px] border-black">
            {/* Header */}
            <div className={`neo-border-b border-b-4 border-black p-2 font-bold text-center ${q.color}`}>
              {q.title} ({qTasks.length})
            </div>
            
            {/* Task list */}
            <div className="p-3 flex-1 space-y-3 overflow-y-scroll">
              {qTasks.length === 0 ? (
                <div className="text-center text-black text-opacity-60 py-6 text-sm italic font-bold">
                  NO TASKS SCHEDULED
                </div>
              ) : (
                qTasks.map((task) => (
                  <div
                    key={task.id}
                    className={`neo-border p-3 neo-shadow transition-all border-black ${
                      task.status === "completed" ? "bg-[#FFF5F5] bg-opacity-50 text-black text-opacity-50" : "bg-[#FFDE4D] text-black"
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <h4 className={`font-bold text-sm ${task.status === "completed" ? "line-through text-opacity-40" : ""}`}>
                        {task.title}
                      </h4>
                      <span className="text-xs font-bold px-1.5 py-0.5 bg-black text-[#FFDE4D]">
                        SCORE: {task.score}
                      </span>
                    </div>

                    <p className={`text-xs mt-1 leading-relaxed ${task.status === "completed" ? "text-opacity-40" : "text-black text-opacity-80"}`}>
                      {task.description}
                    </p>

                    <div className="flex justify-between items-center mt-3 pt-2 border-t border-dashed border-black border-opacity-30 text-[10px] font-bold">
                      <span>DUE: {task.due_date || "N/A"}</span>
                      <span>TIME: {task.estimated_duration} MIN</span>
                    </div>

                    <div className="flex justify-end gap-2 mt-3 pt-2 border-t border-black">
                      <button
                        onClick={() => handleToggleComplete(task)}
                        className="p-1 neo-border bg-[#FFF5F5] hover:bg-[#FFDE4D] text-black border-black"
                        title={task.status === "completed" ? "Mark Pending" : "Mark Complete"}
                      >
                        {task.status === "completed" ? (
                          <CheckCircle2 className="h-4 w-4 text-black" />
                        ) : (
                          <Circle className="h-4 w-4 text-black" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="p-1 neo-border bg-[#FF006E] hover:bg-black hover:text-[#FF006E] text-white border-black"
                        title="Delete Task"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
