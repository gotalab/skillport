"""Search for skills command."""

import typer

from skillport.modules.skills import SearchResult, search_skills

from ..auto_index import ensure_index_fresh
from ..context import get_config
from ..theme import console, create_skills_table, format_score, no_results_panel


def search(
    ctx: typer.Context,
    query: str = typer.Argument(
        ...,
        help="Search query (natural language supported)",
        show_default=False,
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results",
        min=1,
        max=100,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (for scripting/AI agents)",
    ),
):
    """Search for skills matching a query."""
    config = get_config(ctx)
    ensure_index_fresh(ctx, config)
    result: SearchResult = search_skills(query, limit=limit, config=config)

    if json_output:
        console.print_json(data=result.model_dump())
        return

    # No results with suggestions
    if not result.skills:
        console.print(no_results_panel(query))
        return

    # Create styled table with scores
    table = create_skills_table(f"Search: {query}", show_score=True, show_category=False)
    for skill in result.skills:
        desc = skill.description[:45] + "..." if len(skill.description) > 45 else skill.description
        table.add_row(
            skill.id,
            desc,
            format_score(skill.score),
        )

    console.print(table)

    # Show result count
    if len(result.skills) == limit:
        console.print(f"[dim]Showing top {limit} results. Use --limit to see more.[/dim]")
