"use strict";

const revealButton = document.getElementById("reveal-plan");
const planAndReport = document.getElementById("plan-and-report");

if (revealButton && planAndReport) {
  revealButton.addEventListener("click", () => {
    const isExpanded = revealButton.getAttribute("aria-expanded") === "true";
    revealButton.setAttribute("aria-expanded", String(!isExpanded));
    planAndReport.hidden = isExpanded;
    revealButton.querySelector("span").textContent = isExpanded ? "↓" : "↑";
    revealButton.firstChild.textContent = isExpanded
      ? "Create My 7-Day Portfolio Plan "
      : "Hide My 7-Day Portfolio Plan ";

    if (!isExpanded) {
      const planHeading = planAndReport.querySelector("#plan-title");
      planHeading.setAttribute("tabindex", "-1");
      planHeading.focus();
    } else {
      revealButton.focus();
    }
  });
}
