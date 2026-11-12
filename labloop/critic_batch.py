"""Collect a verdict per work product and consolidate IGV follow-up requests."""

from pathlib import Path

from .igv import render_views
from .report_schemas import IgvBatchVerdict, batch_review_schema


def _validated_reviews(report, entries, artifacts):
    reviews = {review.key: review for review in report.reviews}
    if len(reviews) != len(report.reviews) or reviews.keys() != entries.keys():
        raise ValueError("Return exactly one review for each supplied product key")
    for key, review in reviews.items():
        wants_views = isinstance(review, IgvBatchVerdict) and review.igv_views
        if wants_views and review.needs_input:
            raise ValueError(f"{key}: choose an IGV follow-up or scientist input")
        if wants_views and not entries[key]["igv"]["remaining_requests"]:
            raise ValueError(f"{key}: no additional IGV views are available")
        if review.verdict != "uncertain" and not review.evidence and not wants_views:
            raise ValueError(f"{key}: a definite verdict requires an evidence file")
        for path in review.evidence:
            if not path or Path(path).is_absolute():
                raise ValueError(f"{key}: evidence must be a project-relative file path")
            artifacts.evidence_file(path)
    return reviews


def _ask(agent, criteria, context, entries, artifacts, trace, *, igv=False):
    context = {**context, "batch": list(entries.values())}
    schema = batch_review_schema(tuple(entries), igv=igv)
    report = None
    try:
        report = agent.ask("critic", criteria, context, schema, artifacts, trace)
        return _validated_reviews(report, entries, artifacts)
    except ValueError as error:
        correction = {"error": str(error)}
        if report is not None:
            correction["previous_response"] = report.model_dump()
        repair_trace = trace.with_stem(f"{trace.stem}-repair")
        report = agent.ask("critic", criteria, {**context, "correction": correction},
                           schema, artifacts, repair_trace)
        return _validated_reviews(report, entries, artifacts)


def review_batch(agent, criteria, context, artifacts, trace, products, launcher, requests, views):
    entries = {}
    for item in products:
        entry = {"product": item.model_dump()}
        if launcher:
            entry["igv"] = {"views": views[item.key], "remaining_requests": int(item.key in requests),
                            "previous_review": None}
        entries[item.key] = entry
    igv = any(key in requests for key in entries)
    reviews = _ask(agent, criteria, context, entries, artifacts, trace, igv=igv)
    if not igv:
        return reviews

    followup = {}
    renders = []
    for key, review in reviews.items():
        if review.igv_views:
            renders.extend((key, view) for view in review.igv_views)
            followup[key] = entries[key]
    if renders:
        results = render_views(artifacts, launcher, [(requests[key], view) for key, view in renders])
        for (key, _), result in zip(renders, results, strict=True):
            views[key].append(result)
        for key, entry in followup.items():
            entry["igv"].update(remaining_requests=0, previous_review=reviews[key].model_dump())
        followup_trace = trace.with_stem(f"{trace.stem}-view-1")
        reviews.update(_ask(agent, criteria, context, followup, artifacts, followup_trace))
    return reviews
