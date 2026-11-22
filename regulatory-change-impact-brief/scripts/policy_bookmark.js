(() => {
  const {locator, run_id, started} = __SCOPE__;
  const page = location.origin + location.pathname.replace(/\/$/, "");
  if (page !== locator || !/internal polic/i.test(document.title)) {
    return alert("Open the disclosed Current Internal Policies page first.");
  }
  if (performance.timeOrigin < Date.parse(started)) {
    return alert("Refresh the POLICY page for this run, then select the passage again.");
  }
  const passage = String(window.getSelection()).trim();
  if (!passage || passage.length > 8000) {
    return alert("Highlight one relevant policy passage (up to 8,000 characters).");
  }
  const section = prompt("Enter the section heading exactly as displayed:");
  if (!section?.trim() || section.length > 240) return;
  if (!confirm("Save this selected extract locally? Include only permitted policy facts. Check the heading and passage for personal data or credentials.\n\n" + section + "\n\n" + passage)) return;
  const extract = {run_id, locator: page, title: document.title, section: section.trim(), passage,
    page_loaded_at: new Date(performance.timeOrigin).toISOString(), captured_at: new Date().toISOString()};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(extract, null, 2)], {type: "application/json"}));
  a.download = "policy-selection-" + run_id + "-" + Date.now() + ".json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
})();
