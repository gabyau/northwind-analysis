"""Run the whole pipeline: download, clean, analyze, build webpage."""

import build_site
import clean_data
import download_data
import q1_rep_discounts
import q2_discount_effect
import q3_late_shipments


def main():
    """Run every step in order and build the webpage.

    Args:
        None.

    Returns:
        None. Writes ``data/``, ``output/``, and ``docs/``.
    """
    print("\n=== Download data ===")
    download_data.main()
    print("\n=== Clean data ===")
    clean_data.main()

    figures = {}
    for key, name, module in [
        ("q1", "Q1: rep discounting", q1_rep_discounts),
        ("q2", "Q2: discount effect", q2_discount_effect),
        ("q3", "Q3: late shipments", q3_late_shipments),
    ]:
        print(f"\n=== {name} ===")
        figures[key] = module.main()

    print("\n=== Build webpage ===")
    build_site.main(figures)
    print("\nDone. Tables and numbers are in output/; the webpage, with "
          "all three charts, is docs/index.html.")


if __name__ == "__main__":
    main()
