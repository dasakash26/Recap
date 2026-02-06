"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useRecentThreads, useFolders } from "@/hooks/use-chat";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { motion } from "framer-motion";
import { NewChatDialog } from "@/components/new-chat-dialog";
import { SuggestionCard } from "./empty-state/suggestion-card";
import { EmptyStateLoadingSkeleton } from "./empty-state/loading-skeleton";
import { fadeInUp, fadeInStagger } from "@/lib/animation-variants";
import { WelcomeHeader } from "./empty-state/welcome-header";
import { TutorialSection } from "./empty-state/tutorial-section";
import { RecentThreadsList } from "./empty-state/recent-threads-list";
import { FirstChatCard } from "./empty-state/first-chat-card";
import { PromptChips } from "./empty-state/prompt-chips";
import { NewFolderDialog } from "./sidebar/new-folder-dialog";

const SUGGESTION_CHIPS = [
  "Summarize this document",
  "Find key insights",
  "What are the main topics?",
  "Extract important dates",
];

export default function EmptyState() {
  const { data: recentThreads, isLoading: isLoadingThreads } =
    useRecentThreads();
  const { data: folders, isLoading: isLoadingFolders } = useFolders();
  const [isNewChatDialogOpen, setIsNewChatDialogOpen] = useState(false);
  const [isNewFolderDialogOpen, setIsNewFolderDialogOpen] = useState(false);

  if (isLoadingThreads || isLoadingFolders) {
    return <EmptyStateLoadingSkeleton />;
  }

  const hasNoThreads = !recentThreads || recentThreads.length === 0;

  return (
    <div className="flex flex-col h-full w-full bg-background">
      <header className="flex-none h-14 px-4 flex items-center border-b border-border/40 bg-background/80 backdrop-blur-md z-10">
        <SidebarTrigger className="-ml-1" />
      </header>
      <div className="flex flex-col flex-1 overflow-y-auto p-4 md:p-5">
        <motion.div
          className="w-full max-w-2xl mx-auto space-y-4.5"
          variants={fadeInStagger}
          initial="initial"
          animate="animate"
        >
          {/* Welcome Section */}
          <WelcomeHeader
            hasNoThreads={hasNoThreads}
            onNewChat={() => setIsNewChatDialogOpen(true)}
          />

          {/* Tutorial Section - Only show when no threads */}
          {hasNoThreads && <TutorialSection />}

          {/* Recent Threads & Suggestions */}
          <motion.div
            className="flex flex-col gap-3.5 items-stretch"
            variants={fadeInUp}
          >
            {/* Recent Threads - Only show if there are threads */}
            {!hasNoThreads && <RecentThreadsList threads={recentThreads} />}

            {/* Suggestions */}
            <div className="space-y-2.5">
              <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5" />
                {hasNoThreads ? "Get started" : "Quick actions"}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {hasNoThreads ? (
                  <>
                    <FirstChatCard
                      onClick={() => setIsNewChatDialogOpen(true)}
                    />
                    <SuggestionCard
                      title="Create a Folder"
                      description="Organize your documents by creating your first folder."
                      cta="Create folder"
                      onClick={() => setIsNewFolderDialogOpen(true)}
                    />
                  </>
                ) : (
                  <>
                    <SuggestionCard
                      title="New Chat"
                      description="Start a new conversation in any folder."
                      cta="Start chatting"
                      onClick={() => setIsNewChatDialogOpen(true)}
                    />
                    <SuggestionCard
                      title="Create Folder"
                      description="Organize your documents in a new folder."
                      cta="Create folder"
                      onClick={() => setIsNewFolderDialogOpen(true)}
                    />
                  </>
                )}

                {/* Prompt Chips */}
                {hasNoThreads && <PromptChips
                  hasNoThreads={hasNoThreads}
                  prompts={SUGGESTION_CHIPS}
                />}
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>

      <NewChatDialog
        open={isNewChatDialogOpen}
        onOpenChange={setIsNewChatDialogOpen}
        folders={folders}
      />

      <NewFolderDialog
        open={isNewFolderDialogOpen}
        onOpenChange={setIsNewFolderDialogOpen}
      />
    </div>
  );
}
