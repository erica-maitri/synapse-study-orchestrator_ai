import React from "react";
import { playSound } from "../utils/audio";
import { api } from "../utils/api";
import { Calendar, Download, Trash2, Clock } from "lucide-react";

export default function StudyCalendar({ events, onRefresh }) {
  const handleExportICS = () => {
    playSound.success();
    // Redirect to the API export link
    const url = api.getExportUrl();
    window.open(url, "_blank");
  };

  const handleDeleteEvent = async (id) => {
    playSound.click();
    if (confirm("Remove this session from calendar?")) {
      try {
        await api.deleteCalendarEvent(id);
        playSound.success();
        onRefresh();
      } catch (err) {
        playSound.error();
      }
    }
  };

  const formatTime = (isoString) => {
    try {
      const dt = new Date(isoString);
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " (" + dt.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ")";
    } catch (e) {
      return isoString;
    }
  };

  return (
    <div className="flex flex-col bg-[#FFF5F5] p-2 text-black">
      {/* Top action bar */}
      <div className="flex justify-between items-center pb-3 border-b-4 border-black mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          <span className="font-bold text-sm">CALENDAR TIMETABLE ({events.length} SESSIONS)</span>
        </div>
        <button
          onClick={handleExportICS}
          className="neo-btn bg-[#00F5D4] text-black border-black text-xs px-3 py-1.5 flex items-center gap-1.5 hover:bg-black hover:text-[#00F5D4]"
        >
          <Download className="h-4 w-4" />
          EXPORT .ICS
        </button>
      </div>

      {/* Events List */}
      <div className="space-y-3 p-1">
        {events.length === 0 ? (
          <div className="text-center text-black text-opacity-60 py-12 italic text-sm font-bold">
            NO SESSIONS SCHEDULED IN TIMETABLE
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="neo-border bg-[#FFDE4D] p-3 neo-shadow flex justify-between items-center border-black"
            >
              <div className="space-y-1">
                <div className="font-bold text-sm">{event.title}</div>
                {event.description && (
                  <p className="text-xs text-black text-opacity-80">{event.description}</p>
                )}
                <div className="flex items-center gap-1 text-[11px] font-bold text-black bg-[#FFF5F5] px-2 py-0.5 w-fit neo-border border-2 border-black">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{formatTime(event.start_time)} - {formatTime(event.end_time).split(" ")[0]}</span>
                </div>
              </div>

              <button
                onClick={() => handleDeleteEvent(event.id)}
                className="neo-btn p-1.5 bg-[#FF006E] border-black hover:bg-black hover:text-[#FF006E] text-white"
                title="Remove Event"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
