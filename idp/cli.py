from __future__ import annotations

import argparse
import json

from .pipeline import Pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="idp", description="Offline IDP extraction engine")
    ap.add_argument("document", help="path to a PDF / image / docx to extract")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    pipe = Pipeline()
    res = pipe.extract(args.document)
    if not args.quiet:
        print(json.dumps(res.to_dict(), indent=2))
    m = res.metadata
    print(f"\n[{res.document}] template={res.template_id} "
          f"accepted={m['fields_accepted']}/{m['fields_total']} "
          f"review={m['fields_for_review']} -> {m.get('output')}")


if __name__ == "__main__":
    main()
