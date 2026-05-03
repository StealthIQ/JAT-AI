import type { ComponentProps, ReactNode } from "react";

import type { PrimaryNavIndex } from "../app/constants";
import type { UseMonitorRuntimeResult } from "../app/hooks/useMonitorRuntime";
import { ActivityPrimaryView } from "./ActivityPrimaryView";
import { ApisPrimaryView } from "./ApisPrimaryView";
import { CanvasPrimaryView } from "./CanvasPrimaryView";
import { ChatPrimaryView } from "./ChatPrimaryView";
import { PromptsPrimaryView } from "./PromptsPrimaryView";
import { ReposPrimaryView } from "./ReposPrimaryView";
import { SettingsPrimaryView } from "./SettingsPrimaryView";

type PrimaryViewRouterProps = {
  activePrimaryNav: PrimaryNavIndex;
  isMonitorVisible: boolean;
  activityPrimaryViewProps: ComponentProps<typeof ActivityPrimaryView>;
  settingsPrimaryViewProps: ComponentProps<typeof SettingsPrimaryView>;
  canvasPrimaryViewProps: ComponentProps<typeof CanvasPrimaryView>;
  monitorRuntime: Pick<
    UseMonitorRuntimeResult,
    | "monitorConfig"
    | "monitorFeed"
    | "monitorError"
    | "isRefreshingMonitorFeed"
    | "isSavingMonitorConfig"
    | "refreshMonitorFeed"
    | "patchMonitorConfig"
  >;
  conversationsEnabled: boolean;
  onConversationsSidebarContent: (content: ReactNode) => void;
  onConversationsActionPanel: (content: ReactNode) => void;
  promptsEnabled: boolean;
  onPromptsSidebarContent: (content: ReactNode) => void;
};

export const PrimaryViewRouter = ({
  activePrimaryNav,
  isMonitorVisible,
  activityPrimaryViewProps,
  settingsPrimaryViewProps,
  canvasPrimaryViewProps,
  monitorRuntime,
  conversationsEnabled,
  onConversationsSidebarContent,
  onConversationsActionPanel,
  promptsEnabled,
  onPromptsSidebarContent,
}: PrimaryViewRouterProps) => {
  if (activePrimaryNav === 2) {
    return <ReposPrimaryView />;
  }

  if (activePrimaryNav === 3) {
    return <ActivityPrimaryView {...activityPrimaryViewProps} />;
  }

  if (activePrimaryNav === 4) {
    return <ChatPrimaryView />;
  }

  if (activePrimaryNav === 5) {
    return (
      <PromptsPrimaryView enabled={promptsEnabled} onSidebarContent={onPromptsSidebarContent} />
    );
  }

  if (activePrimaryNav === 6) {
    return <ApisPrimaryView />;
  }

  if (activePrimaryNav === 7) {
    return <SettingsPrimaryView {...settingsPrimaryViewProps} />;
  }

  return <CanvasPrimaryView {...canvasPrimaryViewProps} />;
};
