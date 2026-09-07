import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collect.py"
SKILL_ROOT = Path(__file__).resolve().parents[1]
YOUTUBE_CONTENT_SKILL = Path.home() / ".hermes" / "skills" / "media" / "youtube-content" / "SKILL.md"
spec = importlib.util.spec_from_file_location("kb_collect", SCRIPT_PATH)
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


class SaveToObsidianFormatTest(unittest.TestCase):
    def test_text_note_uses_pasted_text_source_and_unified_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            collect.VAULT_PATH = tmp

            path = collect.save_to_obsidian(
                "George pasted this note.",
                "Pasted Note",
                None,
                "owner-note, reflection",
                tldr="A short summary.",
                source_author="George",
            )

            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("source: pasted text\n", text)
            self.assertIn("source_type: text\n", text)
            self.assertIn("title: Pasted Note\n", text)
            self.assertIn("tags:\n  - owner-note\n  - reflection\n", text)
            self.assertIn("# Pasted Note\n", text)
            self.assertIn("## Source Snapshot\n", text)
            self.assertIn("## AI Summary\n", text)
            self.assertIn("<!-- AI Summary (provided) -->", text)
            self.assertIn("## Analysis & Red Team\n", text)
            self.assertIn("<!-- Add analysis and red-team notes here. -->", text)
            self.assertIn("## George Annotation\n", text)
            self.assertIn("<!-- Add George's annotation here. -->", text)
            self.assertIn("## Content\n", text)


class MlxTranscriptionTest(unittest.TestCase):
    def test_defaults_use_requested_mlx_binary_and_model(self):
        self.assertEqual(collect.WHISPER_ENGINE, "mlx")
        self.assertEqual(
            collect.MLX_WHISPER_BIN,
            "/Users/george/venv-mlx-whisper/bin/mlx_whisper",
        )
        self.assertEqual(
            collect.MLX_WHISPER_MODEL,
            "mlx-community/whisper-large-v3-turbo",
        )

    def test_mlx_command_uses_required_flags_and_reads_txt_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "mlx_whisper"
            wav = Path(tmp) / "sample.wav"
            txt = Path(tmp) / "sample.txt"
            binary.touch()
            wav.touch()

            def fake_run(command, **kwargs):
                txt.write_text("transcript from mlx", encoding="utf-8")
                return Mock(stdout="stdout fallback", stderr="")

            with patch.object(collect, "MLX_WHISPER_BIN", str(binary)), patch.object(
                collect.subprocess, "run", side_effect=fake_run
            ) as run:
                result = collect.transcribe_chunk_mlx(str(wav))

            self.assertEqual(result, "transcript from mlx")
            command = run.call_args.args[0]
            self.assertEqual(command[0], str(binary))
            self.assertEqual(command[1], str(wav))
            self.assertIn(
                ["--model", "mlx-community/whisper-large-v3-turbo"],
                [command[i : i + 2] for i in range(len(command) - 1)],
            )
            self.assertIn(
                ["--language", "zh"],
                [command[i : i + 2] for i in range(len(command) - 1)],
            )
            self.assertIn(
                ["--condition-on-previous-text", "False"],
                [command[i : i + 2] for i in range(len(command) - 1)],
            )
            self.assertIn(
                ["--output-format", "txt"],
                [command[i : i + 2] for i in range(len(command) - 1)],
            )
            self.assertIn(
                ["--output-dir", tmp],
                [command[i : i + 2] for i in range(len(command) - 1)],
            )
            call_kwargs = run.call_args.kwargs
            self.assertTrue(call_kwargs.get("check"))
            self.assertTrue(call_kwargs.get("text"))

    def test_mlx_transcription_falls_back_to_stdout_when_txt_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "mlx_whisper"
            wav = Path(tmp) / "sample.wav"
            binary.touch()
            wav.touch()

            with patch.object(collect, "MLX_WHISPER_BIN", str(binary)), patch.object(
                collect.subprocess,
                "run",
                return_value=Mock(stdout="stdout transcript\n", stderr=""),
            ):
                self.assertEqual(
                    collect.transcribe_chunk_mlx(str(wav)), "stdout transcript"
                )

    def test_unsupported_engine_is_rejected(self):
        with patch.object(collect, "WHISPER_ENGINE", "faster"):
            with self.assertRaisesRegex(ValueError, "Unsupported KB_WHISPER_ENGINE"):
                collect.transcribe_audio(__file__)

    def test_youtube_rejects_unsupported_engine_before_network_work(self):
        with patch.object(collect, "WHISPER_ENGINE", "faster"), patch.object(
            collect, "get_video_info"
        ) as get_info, patch.object(collect, "download_youtube_audio") as download, patch(
            "sys.argv", ["collect.py", "youtube", "https://youtu.be/example"]
        ):
            with self.assertRaisesRegex(ValueError, "Unsupported KB_WHISPER_ENGINE"):
                collect.main()

        get_info.assert_not_called()
        download.assert_not_called()

    def test_unsupported_summary_provider_is_rejected(self):
        with patch.object(collect, "AI_PROVIDER", "openai"):
            with self.assertRaisesRegex(ValueError, "Unsupported AI_PROVIDER"):
                collect.summarize_text("source text", "title")

    def test_cleanup_targets_whisper_wav_and_txt_for_any_audio_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "download.webm"
            wav = Path(tmp) / "download_whisper.wav"
            txt = Path(tmp) / "download_whisper.txt"
            audio.touch()
            wav.touch()
            txt.touch()

            self.assertEqual(collect.whisper_wav_path(audio), str(wav))
            collect.cleanup_transcription_artifacts(audio)
            self.assertFalse(wav.exists())
            self.assertFalse(txt.exists())
            self.assertTrue(audio.exists())


class RoutingContractTest(unittest.TestCase):
    def test_contract_covers_preview_persistence_project_and_pasted_text(self):
        contract = (SKILL_ROOT / "references" / "youtube-routing-contract.md").read_text(
            encoding="utf-8"
        )

        required_routes = (
            "Collect <URL>",
            "Collect <URL>, 先給我詳細總結",
            "先不要存，我先看詳細總結",
            "跟 <project> 有關，放桌面",
            "Collect <URL>，跟 <project> 有關，放桌面",
            "Pasted text or a long paragraph",
        )
        for route in required_routes:
            self.assertIn(route, contract)

    def test_youtube_helper_defers_persistent_routing_to_kb_collector(self):
        skill = YOUTUBE_CONTENT_SKILL.read_text(encoding="utf-8")

        self.assertIn("kb-collector/references/youtube-routing-contract.md", skill)
        self.assertNotIn("Always produce Tier 0 + Tier 1.", skill)
        self.assertNotIn("write a project-ready markdown note", skill)

    def test_url_note_preserves_facebook_url_as_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            collect.VAULT_PATH = tmp
            url = "https://www.facebook.com/example/posts/123"

            path = collect.save_to_obsidian(
                "Fetched post text.",
                "Facebook Post",
                url,
                "facebook, social",
                source_author="Facebook",
            )

            text = Path(path).read_text(encoding="utf-8")
            self.assertIn(f"source: {url}\n", text)
            self.assertIn("source_type: facebook\n", text)
            self.assertIn("## Content\n", text)

    def test_youtube_note_records_whisper_transcript_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            collect.VAULT_PATH = tmp

            path = collect.save_to_obsidian(
                "Video transcript.",
                "Video Note",
                "https://www.youtube.com/watch?v=abc123",
                "youtube",
                source_author="Example Channel",
            )

            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("source_type: youtube\n", text)
            self.assertIn("transcript_source: whisper\n", text)
            self.assertIn("## Raw Transcript\n", text)

    def test_note_records_source_publication_date_separately_from_collection_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            collect.VAULT_PATH = tmp

            path = collect.save_to_obsidian(
                "Video transcript.",
                "Video Note",
                "https://www.youtube.com/watch?v=abc123",
                "youtube",
                source_author="Example Channel",
                source_published_at="2026-07-10",
            )

            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("source_published_at: 2026-07-10\n", text)
            self.assertIn("| Published | 2026-07-10 |", text)
            self.assertIn("| Collected | ", text)
            self.assertIn("created: ", text)

    def test_normalize_source_published_at_converts_youtube_date(self):
        self.assertEqual(collect.normalize_source_published_at("20260710"), "2026-07-10")
        self.assertIsNone(collect.normalize_source_published_at("NA"))


if __name__ == "__main__":
    unittest.main()
