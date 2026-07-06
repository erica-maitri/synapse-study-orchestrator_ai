import React, { useState, useEffect } from "react";
import { playSound } from "../utils/audio";
import { api } from "../utils/api";
import { Award, Eye, Plus, Sparkles, RefreshCw, Trash2, Edit, Flame } from "lucide-react";

export default function Flashcards({ cards, onRefresh }) {
  const [mode, setMode] = useState("due"); // "due" or "all"
  const [localCards, setLocalCards] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [streak, setStreak] = useState(0);
  
  // Add/Edit Modals States
  const [showAddForm, setShowAddForm] = useState(false);
  const [frontText, setFrontText] = useState("");
  const [backText, setBackText] = useState("");
  const [subjectText, setSubjectText] = useState("");
  const [imageText, setImageText] = useState("");
  
  const [editingCard, setEditingCard] = useState(null);
  const [editFrontText, setEditFrontText] = useState("");
  const [editBackText, setEditBackText] = useState("");
  const [editSubjectText, setEditSubjectText] = useState("");
  const [editImageText, setEditImageText] = useState("");

  // DB CRUD Table lists & streaks
  const [allCardsList, setAllCardsList] = useState([]);
  const [streakHistory, setStreakHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const activeCard = localCards[currentIndex];

  // Helper to load cards for the current mode
  const loadLocalCards = async (activeMode) => {
    setLoading(true);
    try {
      const isAll = activeMode === "all";
      const cardsData = await api.getDueFlashcards(null, isAll);
      setLocalCards(cardsData);
      setCurrentIndex(0); // Reset index to first card on mode switch or update
      setShowAnswer(false);
    } catch (err) {
      console.error("Failed to load cards for mode", activeMode, err);
    } finally {
      setLoading(false);
    }
  };

  // Helper to load ALL cards for the CRUD manager
  const loadAllCardsList = async () => {
    try {
      const data = await api.getDueFlashcards(null, true);
      setAllCardsList(data);
    } catch (err) {
      console.error("Failed to load database cards", err);
    }
  };

  // Helper to load streak history for heatmap
  const loadStreakHistory = async () => {
    try {
      const data = await api.getVaultHistory(30);
      setStreakHistory(data);
    } catch (err) {
      console.error("Failed to load streak history", err);
    }
  };

  // Sync state when mode changes or parent refresh triggers
  useEffect(() => {
    loadLocalCards(mode);
    loadAllCardsList();
    loadStreakHistory();
  }, [mode, cards]);

  const handleReview = async (quality) => {
    if (!activeCard) return;
    playSound.click();

    try {
      await api.reviewFlashcard(activeCard.id, quality);
      
      // Update local streak and state
      if (quality >= 3) {
        setStreak((prev) => prev + 1);
        playSound.success();
      } else {
        setStreak(0);
        playSound.error();
      }

      setShowAnswer(false);
      onRefresh(); // Trigger parent refresh (updates sidebar count badge)
      await loadLocalCards(mode); // Refresh current queue
      await loadStreakHistory(); // Reload heatmap state
    } catch (err) {
      playSound.error();
    }
  };

  const handleCreateCard = async (e) => {
    e.preventDefault();
    if (!frontText.trim() || !backText.trim()) return;
    playSound.click();

    const subject = subjectText.trim() || "General";
    const image = imageText.trim() || null;
    
    // Repetitions = 0, ease_factor = 2.5, interval = 0, next_review_date = today
    const payload = {
      front: frontText.trim(),
      back: backText.trim(),
      subject: subject,
      image: image,
      repetitions: 0,
      ease_factor: 2.5,
      interval_days: 0
    };

    console.log("[DEBUG] Creating new flashcard manually: Request payload:", payload);

    try {
      const result = await api.createFlashcard(payload);
      console.log("[DEBUG] Flashcard created successfully. Response:", result);
      
      playSound.success();
      setFrontText("");
      setBackText("");
      setSubjectText("");
      setImageText("");
      setShowAddForm(false);
      
      // Refetch parent due cards count, local queue, CRUD table
      onRefresh();
      await loadLocalCards(mode);
      await loadAllCardsList();
    } catch (err) {
      console.error("[DEBUG] Failed to create flashcard:", err);
      playSound.error();
    }
  };

  const openEditModal = (card) => {
    playSound.click();
    setEditingCard(card);
    setEditFrontText(card.front);
    setEditBackText(card.back);
    setEditSubjectText(card.subject || "");
    setEditImageText(card.image || "");
  };

  const handleUpdateCard = async (e) => {
    e.preventDefault();
    if (!editingCard) return;
    playSound.click();

    try {
      await api.updateFlashcard(editingCard.id, {
        front: editFrontText.trim(),
        back: editBackText.trim(),
        subject: editSubjectText.trim() || "General",
        image: editImageText.trim() || null
      });
      playSound.success();
      setEditingCard(null);
      
      onRefresh();
      await loadLocalCards(mode);
      await loadAllCardsList();
    } catch (err) {
      console.error("[DEBUG] Failed to update card:", err);
      playSound.error();
    }
  };

  const handleDeleteCard = async (id) => {
    playSound.click();
    if (confirm("Are you sure you want to permanently delete this flashcard?")) {
      try {
        await api.deleteFlashcard(id);
        playSound.success();
        
        onRefresh();
        await loadLocalCards(mode);
        await loadAllCardsList();
      } catch (err) {
        console.error("[DEBUG] Failed to delete card:", err);
        playSound.error();
      }
    }
  };

  const qualityRatings = [
    { score: 0, label: "0 (Blackout)", color: "border-2 border-black text-black bg-transparent opacity-40" },
    { score: 1, label: "1 (Wrong)", color: "border-2 border-black text-black bg-transparent opacity-70" },
    { score: 2, label: "2 (Barely)", color: "border-2 border-black text-black bg-transparent" },
    { score: 3, label: "3 (Okay)", color: "bg-[#FFF5F5] text-black border-black" },
    { score: 4, label: "4 (Good)", color: "bg-[#00F5D4] text-black border-2 border-black" },
    { score: 5, label: "5 (Perfect)", color: "bg-[#FFDE4D] text-black border-2 border-black" }
  ];

  // Generate date strings for the last 30 calendar days
  const dates = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().split("T")[0]);
  }

  const historyMap = {};
  streakHistory.forEach((h) => {
    historyMap[h.date] = h;
  });

  return (
    <div className="flex flex-col h-full bg-[#FFF5F5] p-2 text-black font-mono">
      {/* Top Header */}
      <div className="flex justify-between items-center pb-2 border-b-4 border-black mb-3">
        <div className="flex items-center gap-1.5 font-bold text-sm">
          <Award className="h-5 w-5 text-[#FFDE4D]" />
          <span>MEMORY VAULT ({localCards.length} {mode === "due" ? "DUE CARDS" : "ALL CARDS"})</span>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            {streak > 0 && mode === "due" && (
              <div className="bg-[#FFDE4D] border-2 border-black px-2 py-0.5 text-[10px] font-bold flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                STREAK: {streak}
              </div>
            )}
            <button
              onClick={() => { playSound.click(); setShowAddForm(true); }}
              className="neo-btn bg-[#00F5D4] text-black border-2 border-black px-2 py-1 text-xs flex items-center gap-1 hover:bg-black hover:text-[#00F5D4] active:translate-y-0.5 rounded-none"
            >
              <Plus className="h-3.5 w-3.5" />
              ADD CARD
            </button>
          </div>
          
          {/* Segmented Toggle Tab Buttons */}
          <div className="flex border-2 border-black font-bold text-[9px] bg-white shadow-[2px_2px_0px_#000]">
            <button
              type="button"
              onClick={() => { playSound.click(); setMode("due"); }}
              className={`px-2 py-0.5 transition-all ${
                mode === "due" 
                  ? "bg-black text-[#FFF5F5]" 
                  : "bg-transparent text-black hover:bg-black hover:bg-opacity-10"
              }`}
            >
              DUE TODAY
            </button>
            <button
              type="button"
              onClick={() => { playSound.click(); setMode("all"); }}
              className={`px-2 py-0.5 transition-all border-l-2 border-black ${
                mode === "all" 
                  ? "bg-black text-[#FFF5F5]" 
                  : "bg-transparent text-black hover:bg-black hover:bg-opacity-10"
              }`}
            >
              BROWSE ALL
            </button>
          </div>
        </div>
      </div>

      {/* NEW CARD MODAL WINDOW */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 font-mono">
          <div className="neo-border bg-[#FFF5F5] w-full max-w-md neo-shadow relative rounded-none border-4 border-black">
            {/* Title Bar */}
            <div className="bg-[#FF006E] text-[#FFF5F5] font-bold text-xs p-2.5 flex justify-between items-center border-b-4 border-black">
              <span className="tracking-wide font-bold">[NEWCARD.EXE] — ADD_CARD</span>
              <button
                onClick={() => { playSound.click(); setShowAddForm(false); }}
                className="p-1 neo-border bg-[#FFF5F5] text-black hover:bg-[#FF006E] hover:text-[#FFF5F5] h-5 w-5 flex items-center justify-center font-bold border-2"
                title="Close"
              >
                X
              </button>
            </div>
            {/* Form */}
            <form onSubmit={handleCreateCard} className="p-4 space-y-4">
              <div>
                <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">FRONT (QUESTION/TERM)</label>
                <textarea
                  value={frontText}
                  onChange={(e) => setFrontText(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black p-2 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                  placeholder="e.g. Newton's Second Law"
                  rows={2}
                  maxLength={500}
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">BACK (ANSWER/DEFINITION)</label>
                <textarea
                  value={backText}
                  onChange={(e) => setBackText(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black p-2 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                  placeholder="e.g. F = ma (Force equals mass times acceleration)"
                  rows={3}
                  maxLength={2000}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">TAG/SUBJECT</label>
                  <input
                    type="text"
                    value={subjectText}
                    onChange={(e) => setSubjectText(e.target.value)}
                    className="w-full bg-[#FFF5F5] border-2 border-black px-2 py-1 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                    placeholder="e.g. Physics"
                    maxLength={100}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">IMAGE URL (OPTIONAL)</label>
                  <input
                    type="text"
                    value={imageText}
                    onChange={(e) => setImageText(e.target.value)}
                    className="w-full bg-[#FFF5F5] border-2 border-black px-2 py-1 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                    placeholder="e.g. https://example.com/law.jpg"
                    maxLength={500}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { playSound.click(); setShowAddForm(false); }}
                  className="neo-btn bg-[#FFF5F5] text-black border-2 border-black px-4 py-1.5 text-xs font-bold hover:bg-black hover:text-[#FFF5F5] active:translate-y-0.5 rounded-none"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="neo-btn bg-[#FF006E] text-white border-2 border-black px-4 py-1.5 text-xs font-bold hover:bg-black hover:text-[#FF006E] active:translate-y-0.5 rounded-none"
                >
                  CREATE
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT CARD MODAL WINDOW */}
      {editingCard && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 font-mono">
          <div className="neo-border bg-[#FFF5F5] w-full max-w-md neo-shadow relative rounded-none border-4 border-black">
            {/* Title Bar */}
            <div className="bg-[#8B5CF6] text-white font-bold text-xs p-2.5 flex justify-between items-center border-b-4 border-black">
              <span className="tracking-wide font-bold">[EDITCARD.EXE] — EDIT_CARD</span>
              <button
                onClick={() => { playSound.click(); setEditingCard(null); }}
                className="p-1 neo-border bg-[#FFF5F5] text-black hover:bg-black hover:text-[#FFF5F5] h-5 w-5 flex items-center justify-center font-bold border-2"
                title="Close"
              >
                X
              </button>
            </div>
            {/* Form */}
            <form onSubmit={handleUpdateCard} className="p-4 space-y-4">
              <div>
                <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">FRONT (QUESTION/TERM)</label>
                <textarea
                  value={editFrontText}
                  onChange={(e) => setEditFrontText(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black p-2 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                  rows={2}
                  maxLength={500}
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">BACK (ANSWER/DEFINITION)</label>
                <textarea
                  value={editBackText}
                  onChange={(e) => setEditBackText(e.target.value)}
                  className="w-full bg-[#FFF5F5] border-2 border-black p-2 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                  rows={3}
                  maxLength={2000}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">TAG/SUBJECT</label>
                  <input
                    type="text"
                    value={editSubjectText}
                    onChange={(e) => setEditSubjectText(e.target.value)}
                    className="w-full bg-[#FFF5F5] border-2 border-black px-2 py-1 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                    maxLength={100}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold mb-1 tracking-wider text-black">IMAGE URL (OPTIONAL)</label>
                  <input
                    type="text"
                    value={editImageText}
                    onChange={(e) => setEditImageText(e.target.value)}
                    className="w-full bg-[#FFF5F5] border-2 border-black px-2 py-1 text-xs font-bold focus:outline-none focus:border-[#FF006E] rounded-none"
                    maxLength={500}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { playSound.click(); setEditingCard(null); }}
                  className="neo-btn bg-[#FFF5F5] text-black border-2 border-black px-4 py-1.5 text-xs font-bold hover:bg-black hover:text-[#FFF5F5] active:translate-y-0.5 rounded-none"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="neo-btn bg-[#FF006E] text-white border-2 border-black px-4 py-1.5 text-xs font-bold hover:bg-black hover:text-[#FF006E] active:translate-y-0.5 rounded-none"
                >
                  UPDATE
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Review Box */}
      <div className="flex-1 flex flex-col justify-center min-h-[220px] max-h-[340px]">
        {localCards.length === 0 ? (
          <div className="neo-border bg-[#FFDE4D] text-black border-black p-8 text-center neo-shadow">
            <Sparkles className="h-8 w-8 text-black mx-auto mb-3" />
            {mode === "due" ? (
              <>
                <h3 className="font-bold text-sm">ALL CARDS REVIEWED!</h3>
                <p className="text-xs text-black text-opacity-80 mt-1">Your memory vault is up to date.</p>
                <button
                  onClick={() => { playSound.click(); onRefresh(); loadLocalCards(mode); }}
                  className="neo-btn bg-[#FF006E] text-white border-black px-4 py-1.5 text-xs font-bold mt-4 inline-flex items-center gap-1 hover:bg-black hover:text-[#FF006E]"
                >
                  <RefreshCw className="h-4 w-4" />
                  CHECK AGAIN
                </button>
              </>
            ) : (
              <>
                <h3 className="font-bold text-sm">NO FLASHCARDS FOUND</h3>
                <p className="text-xs text-black text-opacity-80 mt-1">Click '+ ADD CARD' to create your first flashcard!</p>
              </>
            )}
          </div>
        ) : (
          <div className="flex flex-col justify-between h-full min-h-[220px]">
            {/* Flashcard Box */}
            <div className="neo-border bg-[#FFDE4D] text-black border-black p-4 neo-shadow flex flex-col justify-between min-h-[180px] flex-1">
              {/* Card Content */}
              <div className="text-center flex-1 flex flex-col justify-center py-2">
                <div className="flex flex-wrap gap-1 justify-center mb-2">
                  {activeCard.subject && (
                    <span className="bg-black text-[#00F5D4] text-[8px] font-extrabold px-1.5 py-0.5 border border-black uppercase tracking-wider">
                      {activeCard.subject}
                    </span>
                  )}
                  {mode === "due" && activeCard.days_overdue > 0 && (
                    <span className="bg-[#FF006E] text-white text-[8px] font-extrabold px-1.5 py-0.5 border border-black uppercase tracking-wider animate-pulse">
                      {activeCard.days_overdue} {activeCard.days_overdue === 1 ? 'DAY' : 'DAYS'} OVERDUE
                    </span>
                  )}
                </div>

                {/* Render optional Image */}
                {activeCard.image && (
                  <div className="my-2 max-h-[100px] mx-auto overflow-hidden border-2 border-black bg-white w-fit">
                    <img src={activeCard.image} alt="visual aid" className="max-h-[90px] object-contain rounded-none" />
                  </div>
                )}

                {mode === "all" ? (
                  <div className="space-y-4 py-1 text-left max-w-md mx-auto w-full">
                    <div className="border-b border-black border-dashed pb-2">
                      <div className="text-[8px] font-extrabold text-black text-opacity-50 uppercase tracking-wide">FRONT (QUESTION)</div>
                      <div className="font-bold text-xs mt-0.5 whitespace-pre-wrap">{activeCard.front}</div>
                    </div>
                    <div>
                      <div className="text-[8px] font-extrabold text-[#FF006E] uppercase tracking-wide">BACK (ANSWER)</div>
                      <div className="font-bold text-xs mt-0.5 whitespace-pre-wrap">{activeCard.back}</div>
                    </div>
                  </div>
                ) : (
                  <div className="font-bold text-sm px-4 whitespace-pre-wrap">
                    {showAnswer ? activeCard.back : activeCard.front}
                  </div>
                )}
              </div>

              {/* Action Bar (Only visible in due review mode) */}
              {mode === "due" && (
                <div className="border-t border-black pt-3">
                  {!showAnswer ? (
                    <button
                      onClick={() => { playSound.click(); setShowAnswer(true); }}
                      className="w-full neo-btn bg-[#FF006E] text-white border-black py-2 flex items-center justify-center gap-1.5 text-xs font-bold hover:bg-black hover:text-[#FF006E] active:translate-y-0.5"
                    >
                      <Eye className="h-4 w-4" />
                      REVEAL ANSWER
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <div className="text-[9px] font-bold text-center text-black text-opacity-80">
                        RATE RECALL QUALITY (SM-2 UPDATE)
                      </div>
                      <div className="grid grid-cols-3 gap-1">
                        {qualityRatings.map((rating) => (
                          <button
                            key={rating.score}
                            onClick={() => handleReview(rating.score)}
                            className={`neo-btn py-1 text-[9px] font-bold ${rating.color} active:translate-y-0.5`}
                          >
                            {rating.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Prev/Next Navigation Footer */}
            <div className="border-t-4 border-black pt-3 mt-4 flex items-center justify-between font-mono font-bold text-xs">
              <button
                type="button"
                disabled={currentIndex === 0 || localCards.length === 0}
                onClick={() => { playSound.click(); setCurrentIndex((prev) => prev - 1); setShowAnswer(false); }}
                className={`px-3 py-1.5 border-2 border-black text-xs font-bold transition-all rounded-none ${
                  currentIndex === 0 || localCards.length === 0
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed border-gray-400 opacity-60 shadow-none"
                    : "bg-[#00F5D4] text-black hover:bg-black hover:text-[#00F5D4] shadow-[3px_3px_0px_#000] active:translate-y-0.5 active:shadow-[0px_0px_0px_#000]"
                }`}
              >
                &lt; PREV
              </button>
              
              <span className="text-[10px] font-mono tracking-wider">
                CARD {localCards.length > 0 ? currentIndex + 1 : 0} OF {localCards.length}
              </span>
              
              <button
                type="button"
                disabled={currentIndex === localCards.length - 1 || localCards.length === 0}
                onClick={() => { playSound.click(); setCurrentIndex((prev) => prev + 1); setShowAnswer(false); }}
                className={`px-3 py-1.5 border-2 border-black text-xs font-bold transition-all rounded-none ${
                  currentIndex === localCards.length - 1 || localCards.length === 0
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed border-gray-400 opacity-60 shadow-none"
                    : "bg-[#00F5D4] text-black hover:bg-black hover:text-[#00F5D4] shadow-[3px_3px_0px_#000] active:translate-y-0.5 active:shadow-[0px_0px_0px_#000]"
                }`}
              >
                NEXT &gt;
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 30-DAY REVIEW STREAK HEATMAP */}
      <div className="neo-border bg-[#FFF5F5] border-black p-3 mt-6">
        <h3 className="font-extrabold text-[10px] tracking-wider border-b-2 border-black pb-1.5 mb-3 flex items-center gap-1">
          <Flame className="h-4 w-4 text-[#FF006E] fill-current" />
          LAST 30 DAYS REVIEW ACTIVITY (STREAK HEATMAP)
        </h3>
        
        <div className="flex flex-wrap gap-1.5 justify-center py-2 bg-white p-2 border border-black border-dashed">
          {dates.map((date) => {
            const dayData = historyMap[date] || { cards_reviewed: 0, cards_correct: 0 };
            const reviewed = dayData.cards_reviewed;
            const correct = dayData.cards_correct;
            
            let colorClass = "bg-[#FFF5F5] border border-black border-opacity-30";
            if (reviewed > 0 && reviewed <= 3) colorClass = "bg-[#FFDE4D] border border-black"; // Yellow
            if (reviewed > 3 && reviewed <= 7) colorClass = "bg-[#00F5D4] border border-black"; // Teal
            if (reviewed > 7) colorClass = "bg-[#FF006E] border border-black"; // Pink
            
            const formattedDate = new Date(date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            
            return (
              <div
                key={date}
                className={`h-5 w-5 flex items-center justify-center text-[7px] font-bold ${colorClass} rounded-none relative group`}
                title={`${formattedDate}: ${reviewed} reviewed, ${correct} correct`}
              >
                {/* Micro Tooltip */}
                <span className="hidden group-hover:block absolute bottom-full mb-1 bg-black text-[#FFF5F5] text-[7px] px-1 py-0.5 z-20 border border-black whitespace-nowrap">
                  {formattedDate}: {reviewed} revs
                </span>
              </div>
            );
          })}
        </div>
        
        {/* Heatmap Legend */}
        <div className="flex justify-center items-center gap-4 text-[8px] font-bold mt-2 pt-2 border-t border-black border-opacity-10">
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 bg-[#FFF5F5] border border-black border-opacity-30"></div>
            0 REVIEWS
          </span>
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 bg-[#FFDE4D] border border-black"></div>
            1-3 REVIEWS
          </span>
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 bg-[#00F5D4] border border-black"></div>
            4-7 REVIEWS
          </span>
          <span className="flex items-center gap-1">
            <div className="h-3 w-3 bg-[#FF006E] border border-black"></div>
            8+ REVIEWS
          </span>
        </div>
      </div>

      {/* CRUD MANAGEMENT LIST/TABLE */}
      <div className="neo-border bg-[#FFF5F5] border-black p-3 mt-6">
        <div className="flex justify-between items-center border-b-2 border-black pb-1.5 mb-3">
          <h3 className="font-extrabold text-[10px] tracking-wider">DATABASE MANAGER [FLASHCARDS.DB]</h3>
          <span className="text-[8px] bg-black text-[#FFF5F5] px-1.5 py-0.5 font-bold">TOTAL: {allCardsList.length} CARDS</span>
        </div>
        
        <div className="overflow-y-auto max-h-[220px] border-2 border-black bg-white">
          {allCardsList.length === 0 ? (
            <div className="text-center text-black text-opacity-50 py-6 text-xs italic font-bold">
              NO RECORDS LOADED
            </div>
          ) : (
            <table className="w-full text-left text-[10px] font-bold border-collapse">
              <thead>
                <tr className="bg-black text-[#FFF5F5] text-[9px] uppercase">
                  <th className="p-2 border-r border-b border-black">FRONT / QUESTION</th>
                  <th className="p-2 border-r border-b border-black">BACK / ANSWER</th>
                  <th className="p-2 border-r border-b border-black">SUBJECT</th>
                  <th className="p-2 border-b border-black text-center w-24">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {allCardsList.map((card) => (
                  <tr key={card.id} className="border-b border-black hover:bg-[#FFF5F5]">
                    <td className="p-2 border-r border-black font-mono truncate max-w-[120px]">{card.front}</td>
                    <td className="p-2 border-r border-black font-mono truncate max-w-[120px]">{card.back}</td>
                    <td className="p-2 border-r border-black">
                      <span className="bg-[#FFF5F5] border border-black px-1 text-[8px] uppercase">
                        {card.subject}
                      </span>
                    </td>
                    <td className="p-2 text-center flex items-center justify-center gap-1.5">
                      <button
                        onClick={() => openEditModal(card)}
                        className="p-1 border border-black bg-[#FFDE4D] hover:bg-black hover:text-[#FFDE4D]"
                        title="Edit Card"
                      >
                        <Edit className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => handleDeleteCard(card.id)}
                        className="p-1 border border-black bg-[#FF006E] text-white hover:bg-black hover:text-[#FF006E]"
                        title="Delete Card"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
