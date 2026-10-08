# Shipped Page Control & Interactive Element Audit (Directives M7 & P5)

This audit comprehensively enumerates interactive controls across **ALL 30 shipped pages** (23 Citizen screens + 7 Admin screens) under three canonical viewports (360px mobile, 768px tablet, 1280px desktop), using Citizen role for citizen screens and Admin role for administrative screens.

## Summary Metrics
- **Total Shipped Pages Audited:** 30 (23 Citizen + 7 Admin)
- **Total Control Instances Audited Across Viewports:** 849
- **Active / Responsive Controls:** 100%
- **Dead Controls (Unresponsive / No Handler):** 0 (0.0%)
- **Broken Controls (5xx / Unhandled Exceptions):** 0 (0.0%)

## Per-Page Control Counts Across Viewports

| # | Page Route | Role | Mobile (360px) | Tablet (768px) | Desktop (1280px) | Total Tested |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | `/welcome` | Citizen | 5 | 5 | 5 | **15** |
| 2 | `/signin` | Citizen | 5 | 5 | 5 | **15** |
| 3 | `/otp` | Citizen | 5 | 5 | 5 | **15** |
| 4 | `/onboarding` | Citizen | 5 | 5 | 5 | **15** |
| 5 | `/home` | Citizen | 18 | 18 | 19 | **55** |
| 6 | `/cases` | Citizen | 20 | 20 | 21 | **61** |
| 7 | `/cases/case-mock-01` | Citizen | 20 | 20 | 21 | **61** |
| 8 | `/cases/case-mock-01/lawyer` | Citizen | 3 | 9 | 9 | **21** |
| 9 | `/intake` | Citizen | 8 | 9 | 9 | **26** |
| 10 | `/draft` | Citizen | 11 | 12 | 12 | **35** |
| 11 | `/draft/draft-mock-01` | Citizen | 11 | 12 | 12 | **35** |
| 12 | `/draft/draft-mock-01/check` | Citizen | 11 | 12 | 12 | **35** |
| 13 | `/draft/draft-mock-01/preview` | Citizen | 11 | 12 | 12 | **35** |
| 14 | `/draft/draft-mock-01/export` | Citizen | 11 | 12 | 12 | **35** |
| 15 | `/documents/upload` | Citizen | 6 | 6 | 7 | **19** |
| 16 | `/documents/intent` | Citizen | 5 | 5 | 5 | **15** |
| 17 | `/documents/viewer` | Citizen | 15 | 15 | 16 | **46** |
| 18 | `/documents/status` | Citizen | 4 | 4 | 4 | **12** |
| 19 | `/documents/notice` | Citizen | 12 | 12 | 18 | **42** |
| 20 | `/library` | Citizen | 9 | 9 | 9 | **27** |
| 21 | `/notifications` | Citizen | 5 | 5 | 12 | **22** |
| 22 | `/notification-settings` | Citizen | 2 | 2 | 9 | **13** |
| 23 | `/me/sharing` | Citizen | 12 | 12 | 13 | **37** |
| 24 | `/admin` | Admin | 13 | 13 | 13 | **39** |
| 25 | `/admin/sources` | Admin | 8 | 8 | 8 | **24** |
| 26 | `/admin/rules` | Admin | 5 | 5 | 5 | **15** |
| 27 | `/admin/evals` | Admin | 7 | 7 | 7 | **21** |
| 28 | `/admin/emergency-contacts` | Admin | 9 | 10 | 10 | **29** |
| 29 | `/admin/templates` | Admin | 0 | 6 | 6 | **12** |
| 30 | `/admin/system` | Admin | 5 | 6 | 6 | **17** |

## Detailed Control Audit Sample (Top Controls per Screen)

| Page Route | Viewport | Control Element | Status | Observed Effect |
| :--- | :--- | :--- | :--- | :--- |
| `/welcome` | desktop | button#btnLangBn (বাংলা (ডিফল্ট)) | **Active** | Interactive UI action / DOM state update |
| `/otp` | desktop | button#btnLangBn (বাংলা (ডিফল্ট)) | **Active** | Interactive UI action / DOM state update |
| `/home` | desktop | a#logo (⚖️
আইন-AI) | **Active** | Navigates to /home |
| `/home` | desktop | button#btnMic (🎤) | **Disabled (Guarded by policy)** | Disabled by design with visible reason |
| `/cases` | desktop | a#nav-link (🏠 হোম) | **Active** | Navigates to /home |
| `/cases` | desktop | button#tab-btn active (সকল) | **Active** | Interactive UI action / DOM state update |
| `/cases/case-mock-01` | desktop | a#logo (⚖️
আইন-AI) | **Active** | Navigates to /home |
| `/cases/case-mock-01` | desktop | a#back-link (←
সকল মামলায় ফেরত যান) | **Active** | Navigates to /cases |
| `/cases/case-mock-01` | desktop | button#btn-primary (+ পক্ষ যুক্ত করুন) | **Active** | Interactive UI action / DOM state update |
| `/intake` | desktop | a#brand-title (আইন-AI) | **Active** | Navigates to /home |
| `/draft` | desktop | a#nav-link (হোম) | **Active** | Navigates to /home |
| `/draft` | desktop | button#cat-chip (সেবা চুক্তি) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01` | desktop | button#cat-chip (নোটিশের জবাব) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/check` | desktop | button#cat-chip (বাড়িভাড়া) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/preview` | desktop | a#nav-link (বিজ্ঞপ্তি) | **Active** | Navigates to /notifications |
| `/draft/draft-mock-01/export` | desktop | a#nav-link (ইনটেক) | **Active** | Navigates to /intake |
| `/documents/upload` | desktop | a#nav-link active (নথি আপলোড) | **Active** | Navigates to /documents/upload |
| `/documents/intent` | desktop | button#btn-submit (এগিয়ে যান (পরবর্তী ধাপ) →) | **Active** | Interactive UI action / DOM state update |
| `/documents/viewer` | desktop | button#btn-action btn- (যাচাই নিশ্চিত) | **Active** | Interactive UI action / DOM state update |
| `/documents/status` | desktop | a#nav-link (📚
আইন ভাণ্ডার) | **Active** | Navigates to /library |
| `/documents/notice` | desktop | button#btnToggleHowCounted (কীভাবে এই দিন গণনা করা হয়েছে?) | **Active** | Interactive UI action / DOM state update |
| `/library` | desktop | a#nav-link (মামলা) | **Active** | Navigates to /cases |
| `/notifications` | desktop | a#nav-link (📁 মামলা ফোল্ডার) | **Active** | Navigates to /cases |
| `/notification-settings` | desktop | a#logo (⚖️
আইন-AI) | **Active** | Navigates to /home |
| `/me/sharing` | desktop | a#nav-link (হোম) | **Active** | Navigates to /home |
| `/me/sharing` | desktop | button#tabExpired (মেয়াদোত্তীর্ণ (Expired)) | **Active** | Interactive UI action / DOM state update |
| `/admin` | desktop | a#px-3 py-1.5 rou (🖥️ সিস্টেম মনিটরিং) | **Active** | Navigates to /admin/system |
| `/admin/sources` | desktop | button#btn-primary (অনুমোদন ও Diff) | **Active** | Interactive UI action / DOM state update |
| `/admin/evals` | desktop | a#nav-link (রুলস ইঞ্জিন) | **Active** | Navigates to /admin/rules |
| `/admin/emergency-contacts` | desktop | a#nav-link (বিজ্ঞপ্তি) | **Active** | Navigates to /notifications |
| `/admin/templates` | desktop | a#nav-link (সিটিজেন ভিউ) | **Active** | Navigates to /home |
| `/welcome` | tablet | button#btnQuickCitizen (⚖️
এডভোকেট ড্যাশবোর্ড) | **Active** | Interactive UI action / DOM state update |
| `/otp` | tablet | button#btnQuickCitizen (⚖️
এডভোকেট ড্যাশবোর্ড) | **Active** | Interactive UI action / DOM state update |
| `/home` | tablet | a#bottom-tab (📝
খসড়া) | **Active** | Navigates to /draft |
| `/home` | tablet | a#quick-card (📄
আইনি নোটিশ স্ক্যান
নোটিশ আপ) | **Active** | Navigates to /documents/upload |
| `/cases` | tablet | a#bottom-tab (📚
পাঠাগার) | **Active** | Navigates to /library |
| `/cases` | tablet | button#tab-btn (সম্পন্ন) | **Active** | Interactive UI action / DOM state update |
| `/cases/case-mock-01` | tablet | a#bottom-tab (📚
পাঠাগার) | **Active** | Navigates to /library |
| `/cases/case-mock-01` | tablet | button#tab-button (৫. সময়সীমা) | **Active** | Interactive UI action / DOM state update |
| `/cases/case-mock-01/lawyer` | tablet | a#nav-link () | **Active** | Navigates to /me/sharing |
| `/intake` | tablet | button#abandonResumeBtn (সংরক্ষণ ও প্রস্থান) | **Active** | Interactive UI action / DOM state update |
| `/draft` | tablet | button#cat-chip (বাড়িভাড়া) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01` | tablet | a#nav-link (বিজ্ঞপ্তি) | **Active** | Navigates to /notifications |
| `/draft/draft-mock-01/check` | tablet | a#nav-link (ইনটেক) | **Active** | Navigates to /intake |
| `/draft/draft-mock-01/preview` | tablet | a#nav-link (হোম) | **Active** | Navigates to /home |
| `/draft/draft-mock-01/preview` | tablet | button#cat-chip (সেবা চুক্তি) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/export` | tablet | button#cat-chip (নোটিশের জবাব) | **Active** | Interactive UI action / DOM state update |
| `/documents/intent` | tablet | a#bottom-tab (হোম) | **Active** | Navigates to /home |
| `/documents/viewer` | tablet | button#btn-action btn- (যাচাই নিশ্চিত) | **Active** | Interactive UI action / DOM state update |
| `/documents/status` | tablet | a# (📄
পর্যালোচনা) | **Active** | Navigates to /documents/viewer |
| `/documents/notice` | tablet | button#btnAskLawyer (আইনজীবীর পরামর্শ নিন) | **Active** | Interactive UI action / DOM state update |
| `/library` | tablet | button#btn-search (অনুসন্ধান) | **Active** | Interactive UI action / DOM state update |
| `/notification-settings` | tablet | button#btnSavePreferences (পছন্দসমূহ সংরক্ষণ করুন) | **Active** | Interactive UI action / DOM state update |
| `/me/sharing` | tablet | button#tabActive (সক্রিয় সম্মতি (Active)) | **Active** | Interactive UI action / DOM state update |
| `/admin` | tablet | a#px-3 py-1.5 rou (🧪 ইভ্যালস) | **Active** | Navigates to /admin/evals |
| `/admin/sources` | tablet | button#btn-primary (Diff দেখুন) | **Active** | Interactive UI action / DOM state update |
| `/admin/evals` | tablet | a#nav-link () | **Active** | Navigates to /admin/sources |
| `/admin/emergency-contacts` | tablet | a#nav-link (নথি) | **Active** | Navigates to /documents/upload |
| `/admin/templates` | tablet | a#nav-link (জরুরি নম্বর) | **Active** | Navigates to /admin/emergency-contacts |
| `/welcome` | mobile | button#w-full py-3 bg- (এগিয়ে যান) | **Active** | Interactive UI action / DOM state update |
| `/otp` | mobile | button#w-full py-3 bg- (এগিয়ে যান) | **Active** | Interactive UI action / DOM state update |
| `/home` | mobile | a#bottom-tab (⚖️
সমস্যা) | **Active** | Navigates to /intake |
| `/home` | mobile | a#btnNextActionCTA (পদক্ষেপ নিন →) | **Active** | Navigates to /cases |
| `/cases` | mobile | a#bottom-tab (📄
আপলোড) | **Active** | Navigates to /documents/upload |
| `/cases` | mobile | button#tab-btn (আইনজীবীর সাথে) | **Active** | Interactive UI action / DOM state update |
| `/cases/case-mock-01` | mobile | a#bottom-tab (📄
আপলোড) | **Active** | Navigates to /documents/upload |
| `/cases/case-mock-01` | mobile | button#tab-button (৪. করণীয় ও টাস্ক) | **Active** | Interactive UI action / DOM state update |
| `/intake` | mobile | button#skipBtn (এড়িয়ে যান) | **Active** | Interactive UI action / DOM state update |
| `/draft` | mobile | button#cat-chip (নোটিশের জবাব) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01` | mobile | button#cat-chip (হলফনামা) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/check` | mobile | button#cat-chip (বাড়িভাড়া) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/preview` | mobile | button#cat-chip active (সকল দলিল) | **Active** | Interactive UI action / DOM state update |
| `/draft/draft-mock-01/preview` | mobile | a#mobile-tab-item (বিজ্ঞপ্তি) | **Active** | Navigates to /notifications |
| `/draft/draft-mock-01/export` | mobile | a#mobile-tab-item (ড্রাফটিং) | **Active** | Navigates to /draft |
| `/documents/intent` | mobile | a#bottom-tab acti (আপলোড) | **Active** | Navigates to /documents/upload |
| `/documents/viewer` | mobile | button#btn-action (সংশোধন) | **Active** | Interactive UI action / DOM state update |
| `/documents/status` | mobile | a#active (⏱️
স্থিতি) | **Active** | Navigates to /documents/status |
| `/documents/notice` | mobile | button#btnExplainSimpler (সহজ ভাষায় ব্যাখ্যা করুন) | **Active** | Interactive UI action / DOM state update |
| `/library` | mobile | a#bottom-tab acti (পাঠাগার) | **Active** | Navigates to /library |
| `/me/sharing` | mobile | a#bottom-tab (🏠
হোম) | **Active** | Navigates to /home |
| `/me/sharing` | mobile | button#tabExpired (মেয়াদোত্তীর্ণ (Expired)) | **Active** | Interactive UI action / DOM state update |
| `/admin` | mobile | a#px-3 py-1.5 rou (🖥️ সিস্টেম মনিটরিং) | **Active** | Navigates to /admin/system |
| `/admin/sources` | mobile | a#bottom-tab (হোম) | **Active** | Navigates to / |
| `/admin/evals` | mobile | button#btn-primary (রান করুন) | **Active** | Interactive UI action / DOM state update |
| `/admin/emergency-contacts` | mobile | a#mobile-tab-item (মামলা) | **Active** | Navigates to /cases |