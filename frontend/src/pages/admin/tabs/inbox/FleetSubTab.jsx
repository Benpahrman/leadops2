import React from 'react';
import {
  FleetMetrics,
  FleetWarmupRoadmap,
  DeliverabilitySuite,
  FleetInboxesTable,
} from './fleet';

export default function FleetSubTab({
  inboxes = [],
  warmupCycle,
  handleStartWarmup,
  startingWarmup = false,
  handleDispatchWarmupBatch,
  dispatchingWarmup = false,
  handleRunWarmupMonitoring,
  monitoringWarmup = false,
  deliverabilityReport,
  handleRunDeliverabilityAudit,
  auditingDeliverability = false,
  deliverabilityTab,
  setDeliverabilityTab,
  testCopySubject,
  setTestCopySubject,
  testCopyBody,
  setTestCopyBody,
  handleAuditTestCopy,
  auditingContent = false,
  contentAuditResult,
  handleTestInbox,
  testingInboxId,
  handleDeleteInbox,
}) {
  return (
    <>
      {/* Quick Fleet Metrics */}
      <FleetMetrics inboxes={inboxes} warmupCycle={warmupCycle} />

      {/* Fleet Warmup Progression & Capacity Roadmap */}
      <FleetWarmupRoadmap
        warmupCycle={warmupCycle}
        inboxes={inboxes}
        handleStartWarmup={handleStartWarmup}
        startingWarmup={startingWarmup}
        handleDispatchWarmupBatch={handleDispatchWarmupBatch}
        dispatchingWarmup={dispatchingWarmup}
        handleRunWarmupMonitoring={handleRunWarmupMonitoring}
        monitoringWarmup={monitoringWarmup}
      />

      {/* Enterprise Deliverability & Placement Suite Command Center */}
      <DeliverabilitySuite
        deliverabilityReport={deliverabilityReport}
        handleRunDeliverabilityAudit={handleRunDeliverabilityAudit}
        auditingDeliverability={auditingDeliverability}
        deliverabilityTab={deliverabilityTab}
        setDeliverabilityTab={setDeliverabilityTab}
        testCopySubject={testCopySubject}
        setTestCopySubject={setTestCopySubject}
        testCopyBody={testCopyBody}
        setTestCopyBody={setTestCopyBody}
        handleAuditTestCopy={handleAuditTestCopy}
        auditingContent={auditingContent}
        contentAuditResult={contentAuditResult}
      />

      {/* All Configured Sending Accounts Table */}
      <FleetInboxesTable
        inboxes={inboxes}
        handleTestInbox={handleTestInbox}
        testingInboxId={testingInboxId}
        handleDeleteInbox={handleDeleteInbox}
      />
    </>
  );
}
