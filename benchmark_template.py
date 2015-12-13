from core import perf_benchmark
from measurements import page_cycler
from telemetry import benchmark
import page_sets

class _PageCycler(perf_benchmark.PerfBenchmark):
  options = {{"pageset_repeat": 6}}
  cold_load_percent = 50  # % of page visits for which a cold load is forced

  @classmethod
  def Name(cls):
    return "page_cycler"

  @classmethod
  def AddBenchmarkCommandLineArgs(cls, parser):
    parser.add_option("--report-speed-index",
        action="store_true",
        help="Enable the speed index metric.")

  @classmethod
  def ValueCanBeAddedPredicate(cls, _, is_first_result):
    return cls.cold_load_percent > 0 or not is_first_result

  def CreatePageTest(self, options):
    return page_cycler.PageCycler(
        page_repeat = options.page_repeat,
        pageset_repeat = options.pageset_repeat,
        cold_load_percent = self.cold_load_percent,
        report_speed_index = options.report_speed_index)

@benchmark.Enabled("all")
class PageCyclerUrl{0}(_PageCycler):
  """Benchmarks for various DHTML operations like simple animations."""
  page_set = page_sets.Url{0}PageSet

  @classmethod
  def Name(cls):
    return "page_cycler.url{0}"
