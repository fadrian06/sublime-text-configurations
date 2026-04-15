import re
import sublime
from sublime import View, CompletionList, CompletionItem, Region
from sublime_plugin import EventListener
from typing import List, Set, Tuple, Optional
from sublime_types import Point, KindId


class AlpineJsCompletions(EventListener):
    def get_current_alpine_attribute(self, view: View, pt: Point) -> Tuple[Optional[str], bool]:
        """
        Encuentra el nombre del atributo Alpine en el que se encuentra el cursor.
        Retorna (nombre_del_atributo, esta_dentro_de_comillas).
        """
        limit = max(0, pt - 1500)
        text = view.substr(Region(limit, pt))
        tag_start = text.rfind('<')
        if tag_start == -1: return None, False
        
        tag_context = text[tag_start:]
        
        # Encontrar todas las aperturas de atributos: attr=" o attr='
        matches = list(re.finditer(r'([\w\.:@-]+)\s*=\s*(["\'])', tag_context))
        
        for match in reversed(matches):
            attr_name = match.group(1)
            quote_type = match.group(2)
            start_pos = match.end()
            
            # Contenido desde la apertura hasta el cursor
            content_after_attr = tag_context[start_pos:]
            
            # Si esta comilla no se ha cerrado (contamos cuántas hay después del mismo tipo)
            if content_after_attr.count(quote_type) % 2 == 0:
                is_alpine = attr_name.startswith(('x-', '@', ':'))
                return (attr_name if is_alpine else None), True
                
        return None, False

    def get_active_iteration_vars(self, view: View, pt: Point) -> Set[str]:
        """
        Encuentra las variables de x-for activas en la posición actual.
        """
        vars = set()
        prefix_content = view.substr(Region(0, pt))
        matches = list(re.finditer(r'<template\s+[^>]*x-for\s*=\s*["\']\s*(?:\(([^)]+)\)|(\w+))\s+in', prefix_content, re.IGNORECASE))
        
        for match in reversed(matches):
            between_content = prefix_content[match.end():]
            opens = between_content.lower().count('<template')
            closes = between_content.lower().count('</template')
            if closes <= opens:
                tuple_match, single_match = match.groups()
                if single_match: vars.add(single_match)
                if tuple_match:
                    for v in tuple_match.split(','): vars.add(v.strip())
        return vars

    def on_query_completions(
        self,
        view: View,
        prefix: str,
        locations: List[Point],
    ) -> CompletionList:
        pt = locations[0]
        line_prefix = view.substr(Region(view.line(pt).a, pt))
        
        kind_directive = [KindId.NAMESPACE, 'd', 'Alpine.js Directive']
        kind_property = [KindId.VARIABLE, 'p', 'Alpine.js Property']
        kind_variable = [KindId.VARIABLE, 'v', 'Alpine.js Variable']
        kind_modifier = [KindId.KEYWORD, 'm', 'Modifier']
        kind_event = [KindId.FUNCTION, 'e', 'Event']

        # 1. CONTEXTO: CDN
        if re.search(r'<script\s+[^>]*src=["\'][^"\']*$', line_prefix):
            return CompletionList([CompletionItem(
                "https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js",
                kind=[KindId.MARKUP, 'c', 'CDN'],
                annotation='Alpine.js v3.15.11'
            )])

        # 2. CONTEXTO: Dentro de un VALOR de atributo
        attr_name, is_inside = self.get_current_alpine_attribute(view, pt)
        
        if is_inside:
            if attr_name:
                content = view.substr(Region(0, view.size()))
                properties = set()
                x_data_blocks = re.findall(r'x-data\s*=\s*(?P<q>["\'])(.*?)(?P=q)', content, re.DOTALL)
                for _, block_content in x_data_blocks:
                    properties.update(re.findall(r'(\w+)\s*:', block_content))
                    properties.update(re.findall(r'(?:get|set)?\s*(\w+)\s*\(\)', block_content))
                    properties.update(re.findall(r'(\w+)\s*\([^)]*\)\s*\{', block_content))

                ignored_keys = {'get', 'set', 'return', 'if', 'else', 'this'}
                out = []

                # Caso A: this.
                this_match = re.search(r'\bthis\.(\w*)$', line_prefix)
                if this_match:
                    this_prefix = this_match.group(1).lower()
                    for prop in sorted(list(properties)):
                        if prop not in ignored_keys and prop.lower().startswith(this_prefix):
                            out.append(CompletionItem(prop, kind=kind_property, details='Component Property'))
                    return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)

                # Caso B: Variables normales
                iteration_vars = self.get_active_iteration_vars(view, pt)
                completions = []
                
                for var in sorted(list(iteration_vars)):
                    if var not in ignored_keys:
                        completions.append(CompletionItem(var, kind=kind_variable, details='Iteration Variable'))

                for prop in sorted(list(properties)):
                    if prop not in ignored_keys and prop not in iteration_vars:
                        completions.append(CompletionItem(prop, kind=kind_property, details='Defined in x-data'))
                
                magics = ['$event', '$dispatch', '$nextTick', '$refs', '$el', '$watch', '$root', '$data', '$id']
                for magic in magics:
                    completions.append(CompletionItem(magic, kind=[KindId.SNIPPET, 'v', 'Magic Variable']))

                out = [c for c in completions if c.trigger.lower().startswith(prefix.lower())]
                return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)
            else:
                return CompletionList([], flags=sublime.INHIBIT_WORD_COMPLETIONS)

        # 3. CONTEXTO: NOMBRE de atributo (Modificadores/Eventos)
        last_word = line_prefix.split()[-1] if line_prefix.strip() else ""
        if '.' in last_word:
            attr_base = last_word.split('.')[0]
            if attr_base.startswith(('@', 'x-on:')):
                line_suffix = view.substr(Region(pt, view.line(pt).b))
                has_assignment = bool(re.match(r'^\s*=', line_suffix))
                modifiers = [('prevent', 'preventDefault'), ('stop', 'stopPropagation'), ('outside', 'Outside element'),
                            ('window', 'On window'), ('document', 'On document'), ('once', 'Only once'),
                            ('debounce', '250ms'), ('throttle', 'Throttle 250ms'), ('self', 'Only self')]
                out = [CompletionItem(mod, kind=kind_modifier, details=desc) if has_assignment else 
                       CompletionItem.snippet_completion(mod, mod + '="$1"', kind=kind_modifier, details=desc)
                       for mod, desc in modifiers]
                return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)

        if re.search(r'(?:x-on:|@)[\w-]*$', line_prefix):
            events = ['click', 'submit', 'input', 'change', 'focus', 'blur', 'keydown', 'keyup']
            line_suffix = view.substr(Region(pt, view.line(pt).b))
            has_assignment = bool(re.match(r'^\s*=', line_suffix))
            out = [CompletionItem(event, kind=kind_event) if has_assignment else 
                   CompletionItem.snippet_completion(event, event + '="$1"', kind=kind_event)
                   for event in sorted(events)]
            return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)

        # 4. CONTEXTO: Directivas base x-* 
        if view.match_selector(pt, 'meta.tag'):
            attr_context = view.substr(Region(max(0, pt - 500), pt))
            tag_name_match = re.search(r'<(\w+)[^>]*$', attr_context)
            is_template = tag_name_match and tag_name_match.group(1).lower() == 'template'

            if is_template:
                out = [CompletionItem.snippet_completion('x-for', 'x-for="${1:item} in ${2:items}" :key="${3:$1}"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-if', 'x-if="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-teleport', 'x-teleport="$1"', kind=kind_directive)]
            else:
                out = [CompletionItem.snippet_completion('x-data', 'x-data="{ $1 }"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-init', 'x-init="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-show', 'x-show="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-bind', 'x-bind:$1="$2"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-on', 'x-on:$1="$2"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-text', 'x-text="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-html', 'x-html="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-model', 'x-model="$1"', kind=kind_directive),
                       CompletionItem.snippet_completion('x-modelable', 'x-modelable="$1"', kind=kind_directive),
                       CompletionItem('x-transition', kind=kind_directive),
                       CompletionItem.snippet_completion('x-effect', 'x-effect="$1"', kind=kind_directive),
                       CompletionItem('x-ignore', kind=kind_directive),
                       CompletionItem.snippet_completion('x-ref', 'x-ref="$1"', kind=kind_directive),
                       CompletionItem('x-cloak', kind=kind_directive),
                       CompletionItem.snippet_completion('x-id', 'x-id="$1"', kind=kind_directive)]
            return CompletionList(out)
            
        return CompletionList([])
