# TASK-014-A2: Cascade Replacement Blind Spot Case Study

## Summary
TASK-014-A2 was a cascade replacement of `MainWindow.m_dblZoom` and `MainWindow.m_dblnum` references to `MainWindowState.Instance.mDblZoom` and `MainWindowState.Instance.mDblnum` across all Views files.

## What Happened

### Round 1 (Failed — QA REJECTED)
- **vpos_core** processed only the 12 files listed in the dispatch context
- **Missed 9 additional files** (48 more references)
- TakeawaysDetail.axaml.cs: half-done (mDblZoom replaced, m_dblnum missed)
- MainWindow.axaml.cs: L2826 missed + proxy stubs not deleted
- 8 other files completely untouched

### Round 2 (Re-dispatched with full grep)
- vpos_lead first ran `grep -r` to find ALL remaining references
- Dispatched to vpos_core with explicit instruction to grep the full Views directory
- Awaiting QA re-review

## Root Cause
The subagent treated the pre-computed file list as the complete scope. It did not independently scan the full directory. This is a "context-bound blind spot" — the agent's cognitive scope was anchored to the provided list.

## Lesson (now Trap 29)
For cascade replacements involving many files:
1. **vpos_lead must**: Before dispatching, run `grep -r` to get the complete file list
2. **In the dispatch goal**: Explicitly instruct the subagent to first grep the full directory for the complete list, not just process the provided list
3. **In Definition of Done**: Include a final `grep -r ... | wc -l` verification that must equal 0
4. **vpos_lead must verify**: After subagent reports done, independently run `grep -r` to confirm no remaining references

## Files Involved (Full List — 21 files)
### Round 1 completed (12 files)
TakeawaysDetail.axaml.cs, TakeawayOrderList.axaml.cs, OrderStagingList.axaml.cs, OrderPrint.axaml.cs, FoodMeal.axaml.cs, Payment.axaml.cs, SysCustomerPanel.axaml.cs, SysNCCC.axaml.cs, SysKDS.axaml.cs, SysInvoice.axaml.cs, SysEasyCard.axaml.cs, SysBasic.axaml.cs

### Round 1 missed (9 files)
TakeawaysDetail.axaml.cs (partial — m_dblnum only), QrorderDetail.axaml.cs, Loading.axaml.cs, Login.axaml.cs, DiDiEats_OrderInfo.axaml.cs, ClosingHandover.axaml.cs, MainWindow.axaml.cs (L2826 + stubs), DiDiEats.axaml.cs, ModifyCart.axaml.cs

## Timeline
- Dispatched: 2026-08-19 13:44:21
- Completed: 2026-08-19 13:53:14 (8m33s)
- QA REJECTED: 2026-08-19 14:09:24
- Re-dispatched: 2026-08-19 14:10:00
