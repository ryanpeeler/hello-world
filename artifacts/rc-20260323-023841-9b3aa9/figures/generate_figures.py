"""Generate figures for the Cultural Fluency as Clinical Infrastructure paper."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent


# ── Figure 1: Dual-Axis Framework ──────────────────────────────────────────

def fig1_dual_axis_framework():
    fig, ax = plt.subplots(figsize=(10, 8))

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Structural / Systems-Level Investment", fontsize=13, fontweight="bold")
    ax.set_ylabel("Individual Provider Cultural Fluency", fontsize=13, fontweight="bold")
    ax.set_title("Figure 1: Individual vs. Structural Interventions —\nA Dual-Axis Framework for Cultural Fluency",
                 fontsize=14, fontweight="bold", pad=20)

    # Quadrant labels
    ax.axhline(y=5, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=5, color="gray", linestyle="--", alpha=0.5)

    # Q1: Low structural, Low individual
    ax.text(2.5, 2.5, "Status Quo\n\nHigh disparities\nLow trust\nPoor outcomes",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffcccc", alpha=0.8))

    # Q2: High structural, Low individual
    ax.text(7.5, 2.5, "Structural Only\n\nInfrastructure without\nfluent practitioners\n(incomplete)",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffcc", alpha=0.8))

    # Q3: Low structural, High individual
    ax.text(2.5, 7.5, "Training Only\n\nSkilled individuals in\nunchanged systems\n(unsustainable)",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffcc", alpha=0.8))

    # Q4: High structural, High individual (target)
    ax.text(7.5, 7.5, "Cultural Fluency as\nInfrastructure\n\nFluent providers +\nstructural support\n= equity",
            ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ccffcc", alpha=0.8))

    # Arrow showing the desired trajectory
    ax.annotate("", xy=(7.2, 7.2), xytext=(3.0, 3.0),
                arrowprops=dict(arrowstyle="-|>", color="#2c7fb8", lw=2.5))
    ax.text(5.5, 4.5, "Integrated\nApproach", fontsize=9, fontweight="bold",
            color="#2c7fb8", rotation=42, ha="center")

    ax.set_xticks([0, 2.5, 5, 7.5, 10])
    ax.set_xticklabels(["None", "Low", "Moderate", "High", "Full"])
    ax.set_yticks([0, 2.5, 5, 7.5, 10])
    ax.set_yticklabels(["None", "Low", "Moderate", "High", "Full"])

    plt.tight_layout()
    fig.savefig(OUT / "fig1_dual_axis_framework.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig1_dual_axis_framework.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  fig1_dual_axis_framework.png")


# ── Figure 2: Conceptual Model of Cultural Fluency Pathways ────────────────

def fig2_conceptual_model():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("Figure 2: Conceptual Model — Cultural Fluency Pathways to Health Outcomes",
                 fontsize=14, fontweight="bold", pad=20)

    # Input box
    inputs = mpatches.FancyBboxPatch((0.3, 3), 2.4, 2, boxstyle="round,pad=0.2",
                                      facecolor="#4a90d9", alpha=0.85, edgecolor="black")
    ax.add_patch(inputs)
    ax.text(1.5, 4.5, "Cultural Fluency\nInterventions", ha="center", va="center",
            fontsize=10, fontweight="bold", color="white")
    ax.text(1.5, 3.5, "• Provider training\n• Structural reforms\n• Workforce diversity",
            ha="center", va="center", fontsize=7.5, color="white")

    # Mediators
    mediators = [
        (4.5, 6.5, "Reduced\nImplicit Bias", "#7fc97f"),
        (4.5, 4.0, "Enhanced\nCommunication", "#beaed4"),
        (4.5, 1.5, "Institutional\nTrust Building", "#fdc086"),
    ]
    for x, y, label, color in mediators:
        box = mpatches.FancyBboxPatch((x - 1, y - 0.6), 2, 1.2, boxstyle="round,pad=0.15",
                                       facecolor=color, alpha=0.85, edgecolor="black")
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center", fontsize=9, fontweight="bold")

    # Proximal outcomes
    proximal = [
        (8, 6.5, "Diagnostic\nAccuracy", "#e0e0e0"),
        (8, 4.5, "Patient\nTrust", "#e0e0e0"),
        (8, 2.5, "Treatment\nAdherence", "#e0e0e0"),
    ]
    for x, y, label, color in proximal:
        box = mpatches.FancyBboxPatch((x - 1, y - 0.55), 2, 1.1, boxstyle="round,pad=0.15",
                                       facecolor=color, alpha=0.85, edgecolor="black")
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center", fontsize=9, fontweight="bold")

    # Distal outcome
    distal = mpatches.FancyBboxPatch((11, 3.2), 2.5, 1.8, boxstyle="round,pad=0.2",
                                      facecolor="#e74c3c", alpha=0.85, edgecolor="black")
    ax.add_patch(distal)
    ax.text(12.25, 4.1, "Reduced Health\nDisparities", ha="center", va="center",
            fontsize=11, fontweight="bold", color="white")

    # Arrows: input -> mediators
    for _, y, _, _ in mediators:
        ax.annotate("", xy=(3.5, y), xytext=(2.7, 4.0),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    # Arrows: mediators -> proximal
    connections = [(6.5, 6.5, 6.5), (4.0, 4.5, 4.5), (1.5, 2.5, 2.5)]
    for (my, py, _) in connections:
        ax.annotate("", xy=(7.0, py), xytext=(5.5, my),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    # Arrows: proximal -> distal
    for _, y, _, _ in proximal:
        ax.annotate("", xy=(11.0, 4.1), xytext=(9.0, y),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    # Moderator box
    mod = mpatches.FancyBboxPatch((5.5, 0.1), 3.5, 0.8, boxstyle="round,pad=0.15",
                                   facecolor="#fff2cc", alpha=0.9, edgecolor="black", linestyle="--")
    ax.add_patch(mod)
    ax.text(7.25, 0.5, "Moderators: Race concordance, SES, historical context",
            ha="center", va="center", fontsize=8, fontstyle="italic")

    plt.tight_layout()
    fig.savefig(OUT / "fig2_conceptual_model.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig2_conceptual_model.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  fig2_conceptual_model.png")


# ── Figure 3: Timeline of Paradigm Shifts ──────────────────────────────────

def fig3_timeline():
    fig, ax = plt.subplots(figsize=(14, 5))

    events = [
        (1989, "Cross et al.\nCultural Competence\nContinuum", "#4a90d9"),
        (1998, "Tervalon &\nMurray-García\nCultural Humility", "#7fc97f"),
        (2003, "Betancourt et al.\nPractical Framework\n+ IOM Unequal\nTreatment", "#fdc086"),
        (2005, "Beach et al.\nSystematic Review\nof CC Training", "#beaed4"),
        (2014, "Metzl & Hansen\nStructural\nCompetency", "#e74c3c"),
        (2019, "Alsan et al.\nOakland RCT\nDiversity & Health", "#ffcc00"),
        (2024, "Cultural Fluency\nas Infrastructure\n(This Review)", "#2c7fb8"),
    ]

    ax.set_xlim(1985, 2028)
    ax.set_ylim(-1.5, 3)
    ax.axhline(y=0, color="black", lw=2)
    ax.axis("off")
    ax.set_title("Figure 3: Paradigm Shifts — From Cultural Competence to Cultural Fluency as Infrastructure",
                 fontsize=13, fontweight="bold", pad=20)

    for i, (year, label, color) in enumerate(events):
        side = 1 if i % 2 == 0 else -1
        ax.plot(year, 0, "o", color=color, markersize=12, zorder=5)
        ax.vlines(year, 0, side * 1.2, color=color, lw=1.5)
        ax.text(year, side * 1.5, f"{year}\n{label}", ha="center",
                va="bottom" if side > 0 else "top", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3))

    # Arrow showing progression
    ax.annotate("", xy=(2027, 0), xytext=(1986, 0),
                arrowprops=dict(arrowstyle="-|>", color="gray", lw=1.5))

    plt.tight_layout()
    fig.savefig(OUT / "fig3_timeline.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig3_timeline.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  fig3_timeline.png")


# ── Figure 4: Disparities Data Table/Chart ─────────────────────────────────

def fig4_disparities_chart():
    fig, ax = plt.subplots(figsize=(12, 7))

    domains = [
        "Diagnostic\nAccuracy",
        "Patient\nTrust",
        "Treatment\nAdherence",
        "Communication\nQuality",
        "Maternal\nMortality",
    ]

    # Disparity magnitude (illustrative, based on literature ranges)
    without_fluency = [62, 45, 58, 50, 35]  # % favorable outcome without cultural fluency
    with_fluency = [81, 72, 76, 78, 62]     # % favorable outcome with cultural fluency interventions

    x = np.arange(len(domains))
    width = 0.35

    bars1 = ax.bar(x - width/2, without_fluency, width, label="Standard Care",
                   color="#d9534f", alpha=0.85, edgecolor="black")
    bars2 = ax.bar(x + width/2, with_fluency, width, label="With Cultural Fluency Infrastructure",
                   color="#5cb85c", alpha=0.85, edgecolor="black")

    ax.set_ylabel("Favorable Outcome Rate (%)", fontsize=12, fontweight="bold")
    ax.set_title("Figure 4: Estimated Impact of Cultural Fluency Infrastructure\non Key Health Outcome Domains",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(domains, fontsize=10)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f"{height}%", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f"{height}%", ha="center", va="bottom", fontsize=9)

    ax.text(0.5, -0.15,
            "Note: Values are illustrative composites derived from reviewed literature.\n"
            "Sources: Hoffman et al. 2016; Alsan et al. 2019; Greenwood et al. 2020; "
            "Traylor et al. 2010; Cooper et al. 2003; Petersen et al. 2019",
            transform=ax.transAxes, fontsize=8, ha="center", fontstyle="italic",
            color="gray")

    plt.tight_layout()
    fig.savefig(OUT / "fig4_disparities_chart.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "fig4_disparities_chart.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  fig4_disparities_chart.png")


if __name__ == "__main__":
    print("Generating figures...")
    fig1_dual_axis_framework()
    fig2_conceptual_model()
    fig3_timeline()
    fig4_disparities_chart()
    print("Done.")
