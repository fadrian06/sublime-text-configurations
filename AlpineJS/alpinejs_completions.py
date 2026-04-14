from sublime import View, CompletionList, CompletionItem, CompletionFormat
from sublime_plugin import EventListener
from typing import List
from sublime_types import Point, KindId


class AlpineJsCompletions(EventListener):
    def on_query_completions(
        self,
        view: View,
        prefix: str,
        locations: List[Point],
    ) -> CompletionList:
        if not view.match_selector(locations[0], 'text.html meta.tag.block.any.html punctuation.definition.tag.end.html'):
            return []

        kind = [KindId.NAMESPACE, 'a', 'Alpine.js Directive']

        available_completions = [
            CompletionItem.snippet_completion(
                'x-data',
                'x-data="{ $1 }"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-init',
                'x-init="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-show',
                'x-show="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-bind',
                'x-bind:$1="$2"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-on',
                'x-on:$1="$2"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-text',
                'x-text="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-html',
                'x-html="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-model',
                'x-model="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-modalable',
                'x-modalable="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-for',
                'x-for="$1"',
                kind=kind
            ),
            CompletionItem('x-transition', kind=kind),
            CompletionItem.snippet_completion(
                'x-effect',
                'x-effect="$1"',
                kind=kind,
            ),
            CompletionItem('x-ignore', kind=kind),
            CompletionItem.snippet_completion(
                'x-ref',
                'x-ref="$1"',
                kind=kind,
            ),
            CompletionItem('x-cloak', kind=kind),
            CompletionItem.snippet_completion(
                'x-teleport',
                'x-teleport="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-if',
                'x-if="$1"',
                kind=kind,
            ),
            CompletionItem.snippet_completion(
                'x-id',
                'x-id="$1"',
                kind=kind,
            ),
        ]

        prefix = prefix.lower()

        out = []

        for comp in available_completions:
            if comp.trigger.lower().startswith(prefix):
                out.append(comp)

        return CompletionList(out)
