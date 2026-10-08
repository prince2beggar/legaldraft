from pathlib import Path

targets = [
    (
        "s9_recipient_viewer_mobile_360.png",
        "360x640 Recipient Viewer: Plain mobile view with Bangla watermark overlay and strictly confirmed data",
    ),
    (
        "s9_recipient_viewer_desktop_1280.png",
        "1280x800 Recipient Viewer: Plain desktop view without citizen shell or owner nav, watermark overlay",
    ),
    (
        "s9_recipient_expired_mobile_360.png",
        "360x640 Recipient Expired/Revoked: Indistinguishable 404 security state (anti-enumeration)",
    ),
    (
        "s9_consentsheet_mobile_360.png",
        "360x640 ConsentSheet: Mobile bottom sheet with scope checkboxes, recipient contact, duration slider, OTP gate",
    ),
    (
        "s9_case_brief_desktop_1280.png",
        "1280x800 Case Brief Editor & Preview (/cases/:id/lawyer): Verified facts, timeline, AI advisory disclaimer, export buttons",
    ),
    (
        "s9_sharing_management_mobile_360.png",
        "360x640 Sharing Management (/me/sharing): Mobile view with Active/Expired/Revoked tabs and instant revoke button",
    ),
    (
        "s9_sharing_management_desktop_1280.png",
        "1280x800 Sharing Management (/me/sharing): Desktop view with active shares table, access count, and audit log link",
    ),
    (
        "s9_admin_system_desktop_1280.png",
        "1280x800 Admin Observability (/admin/system): System health, queue depth, SMS delivery stats, feature flags, p95 latencies",
    ),
    (
        "s9_admin_system_mobile_360.png",
        "360x640 Admin Observability (/admin/system): Responsive mobile system metrics cards",
    ),
]

base_dir = Path("storage/screenshots")
print("| File Name | Path | Dimensions / Viewport | Size (KB) | What it shows |")
print("|---|---|---|---|---|")
for fname, desc in targets:
    fpath = base_dir / fname
    if fpath.exists():
        size_kb = fpath.stat().st_size / 1024
        vp = "360x640" if "360" in fname else ("1280x800" if "1280" in fname else "768x1024")
        print(f"| `{fname}` | `storage/screenshots/{fname}` | {vp} | {size_kb:.1f} KB | {desc} |")
    else:
        print(f"| `{fname}` | MISSING | - | - | {desc} |")
