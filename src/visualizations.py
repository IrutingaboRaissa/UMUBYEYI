"""Object-oriented, reproducible figures for screening experiments."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class ExperimentVisualizer:
    """Create and save the complete figure set for one ML experiment."""

    def __init__(self, dpi: int = 180, colors: dict[str, str] | None = None):
        self.dpi = dpi
        self.colors = colors or {"elevated": "#704f6f", "not_elevated": "#d8a48f"}

    def save(self, fig, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)

    def create_experiment_figures(self, df, y, split_sizes, validation,
                                  report_dir, title) -> None:
        out = Path(report_dir) / "figures"
        out.mkdir(parents=True, exist_ok=True)
        self._class_distribution(y, out)
        self._data_split(split_sizes, out)
        self._missing_values(df, out)
        self._age_distribution(df, y, out)
        self._model_comparison(validation, out, title)
        self._training_times(validation, out, title)
        self._validation_confusion_matrices(validation, out)

    def _class_distribution(self, y, out: Path) -> None:
        counts = y.value_counts().reindex(["elevated", "not_elevated"])
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(["Elevated", "Not elevated"], counts,
                      color=[self.colors[key] for key in counts.index])
        ax.bar_label(bars)
        ax.set(title="Target class distribution", ylabel="Participants")
        self.save(fig, out / "01_target_distribution.png")

    def _data_split(self, split_sizes, out: Path) -> None:
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(split_sizes.keys(), split_sizes.values(),
                      color=["#704f6f", "#a77887", "#d8a48f"])
        ax.bar_label(bars)
        ax.set(title="Stratified 70/15/15 data split", ylabel="Rows")
        self.save(fig, out / "02_data_split.png")

    def _missing_values(self, df, out: Path) -> None:
        missing = df.isna().sum().sort_values(ascending=False).head(15)
        fig, ax = plt.subplots(figsize=(9, 5))
        if missing.max() == 0:
            ax.text(.5, .5, "No missing values in the dataset", ha="center", va="center", fontsize=14)
            ax.axis("off")
        else:
            missing.sort_values().plot.barh(ax=ax, color="#a77887")
            ax.set(xlabel="Missing values", title="Features with the most missing values")
        self.save(fig, out / "03_missing_values.png")

    def _age_distribution(self, df, y, out: Path) -> None:
        if "Age" not in df:
            return
        age = pd.to_numeric(df["Age"], errors="coerce")
        fig, ax = plt.subplots(figsize=(7, 4))
        for label in ("elevated", "not_elevated"):
            ax.hist(age[y == label].dropna(), bins=12, alpha=.65,
                    label=label.replace("_", " "), color=self.colors[label])
        ax.set(title="Age distribution by target class", xlabel="Age", ylabel="Participants")
        ax.legend()
        self.save(fig, out / "04_age_by_target.png")

    def _model_comparison(self, validation, out: Path, title: str) -> None:
        metrics = ["accuracy", "precision", "recall", "f1_score"]
        table = pd.DataFrame(validation).T[metrics]
        fig, ax = plt.subplots(figsize=(12, 6))
        table.plot.bar(ax=ax, color=["#4f6d7a", "#d8a48f", "#704f6f", "#8fb996"])
        ax.set(title=f"{title}: validation metrics", ylabel="Score", xlabel="Model", ylim=(0, 1))
        ax.axhline(.5, color="grey", linewidth=.8, linestyle="--")
        ax.legend(["Accuracy", "Precision", "Recall", "F1 score"], ncol=4)
        ax.tick_params(axis="x", rotation=30)
        self.save(fig, out / "05_validation_model_comparison.png")

    def _training_times(self, validation, out: Path, title: str) -> None:
        timings = pd.Series({name: result.get("fit_seconds", 0) for name, result in validation.items()})
        fig, ax = plt.subplots(figsize=(10, 5))
        timings.sort_values().plot.barh(ax=ax, color="#4f6d7a")
        ax.set(title=f"{title}: training time on 560 rows", xlabel="Seconds", ylabel="Model")
        self.save(fig, out / "07_model_training_time.png")

    def _validation_confusion_matrices(self, validation, out: Path) -> None:
        for index, (name, result) in enumerate(validation.items(), start=1):
            path = out / f"model_{index:02d}_{name}_validation_confusion_matrix.png"
            self._confusion_matrix(result["confusion_matrix"], name, "Validation", "Purples", path)

    def create_test_confusion_figure(self, test_result, report_dir, selected_model) -> None:
        path = Path(report_dir) / "figures" / "06_selected_model_test_confusion_matrix.png"
        self._confusion_matrix(test_result["confusion_matrix"], selected_model,
                               "Untouched test", "Greens", path)

    def _confusion_matrix(self, values, model_name: str, split_name: str,
                          color_map: str, path: Path) -> None:
        matrix = np.asarray(values)
        fig, ax = plt.subplots(figsize=(5, 4.4))
        image = ax.imshow(matrix, cmap=color_map, vmin=0, vmax=max(1, matrix.max()))
        for row in range(2):
            for col in range(2):
                ax.text(col, row, str(matrix[row, col]), ha="center", va="center",
                        color="white" if matrix[row, col] > matrix.max() / 2 else "black", fontsize=14)
        ax.set_xticks([0, 1], ["Elevated", "Not elevated"])
        ax.set_yticks([0, 1], ["Elevated", "Not elevated"])
        ax.set(xlabel="Predicted class", ylabel="Actual class",
               title=f"{split_name} confusion matrix\n{model_name.replace('_', ' ').title()}")
        fig.colorbar(image, ax=ax, fraction=.046, pad=.04)
        self.save(fig, path)

default_visualizer = ExperimentVisualizer()


def create_experiment_figures(df, y, split_sizes, validation, report_dir, title):
    """Backward-compatible training-script entry point."""
    return default_visualizer.create_experiment_figures(df, y, split_sizes, validation, report_dir, title)


def create_test_confusion_figure(test_result, report_dir, selected_model):
    """Backward-compatible training-script entry point."""
    return default_visualizer.create_test_confusion_figure(test_result, report_dir, selected_model)
