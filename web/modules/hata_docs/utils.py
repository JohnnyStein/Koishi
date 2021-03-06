# -*- coding: utf-8 -*-
from html import escape as html_escape

from hata.backend.quote import quote
from hata.ext.patchouli import map_module, MAPPED_OBJECTS, ModuleUnit, QualPath, FunctionUnit, ClassAttributeUnit, \
    InstanceAttributeUnit, TypeUnit, PropertyUnit, search_paths
from hata.ext.patchouli.parser import ATTRIBUTE_SECTION_NAME_RP

UNIT_TYPE_ORDER_PRIO_TYPE = 0

UNIT_TYPE_ORDER_PRIO_FUNCTION = 10
UNIT_TYPE_ORDER_PRIO_PROPERTY = 11
UNIT_TYPE_ORDER_PRIO_METHOD = 12

UNIT_TYPE_ORDER_PRIO_INSTANCE_ATTRIBUTE = 20
UNIT_TYPE_ORDER_PRIO_CLASS_ATTRIBUTE = 21

UNIT_TYPE_ORDER_PRIO_MODULE = 30

UNIT_TYPE_ORDER_PRIO_NONE = 100

UNIT_TYPE_ORDER_PRIO_TYPE_NAME_RELATION = {
    ModuleUnit : ('module', UNIT_TYPE_ORDER_PRIO_MODULE),
    TypeUnit : ('class', UNIT_TYPE_ORDER_PRIO_TYPE),
    PropertyUnit : ('property', UNIT_TYPE_ORDER_PRIO_PROPERTY),
    InstanceAttributeUnit : ('attribute', UNIT_TYPE_ORDER_PRIO_INSTANCE_ATTRIBUTE),
    ClassAttributeUnit : ('class attribute', UNIT_TYPE_ORDER_PRIO_CLASS_ATTRIBUTE),
        }

CLASS_ATTRIBUTE_SECTION_PRIOS = {
    'Class Attributes' : 0,
    'Type Attributes' : 1,
    'Attributes' : 2,
    'Instance Attributes' : 3,
        }

CLASS_ATTRIBUTE_SECTION_DEFAULT = 4

def get_backpath(unit):
    parts = [(unit.name, '#')]
    
    counter = 1
    while True:
        unit = unit.parent
        if unit is None:
            break
        
        parts.append((unit.name, '../'*counter+quote(unit.name)))
        counter += 1
        continue
    
    result = []
    index = len(parts)-1
    while True:
        name, url = parts[index]
        result.append('<a href="')
        result.append(url)
        result.append('">')
        result.append(html_escape(name))
        result.append('</a>')
        
        if index == 0:
            break
        
        index -= 1
        result.append(' / ')
        continue
    
    return ''.join(result)

def get_searched_info(path):
    unit = MAPPED_OBJECTS.get(path)
    if unit is None:
        type_ = None
        order_prio = 100
    else:
        unit_type = type(unit)
        if unit_type is FunctionUnit:
            parent = path.parent
            parent_unit = MAPPED_OBJECTS.get(parent)
            if parent_unit is None:
                type_ = 'function'
                order_prio = UNIT_TYPE_ORDER_PRIO_FUNCTION
            elif type(parent_unit) is TypeUnit:
                type_ = 'method'
                order_prio = UNIT_TYPE_ORDER_PRIO_METHOD
            else:
                type_ = 'function'
                order_prio = UNIT_TYPE_ORDER_PRIO_FUNCTION
        else:
            try:
                type_, order_prio = UNIT_TYPE_ORDER_PRIO_TYPE_NAME_RELATION[unit_type]
            except KeyError:
                type_ = None
                order_prio = UNIT_TYPE_ORDER_PRIO_NONE
    
    backfetched = []
    while True:
        parent = path.parent
        parent_unit = MAPPED_OBJECTS.get(parent)
        if parent_unit is None:
            break
        
        if type(parent_unit) is ModuleUnit:
            break
        
        backfetched.append(path.parts[-1])
        path = parent
        continue
    
    url_parts = []
    name_parts = []
    
    parts = path.parts
    limit = len(parts)
    if limit:
        index = 0
        while True:
            part = parts[index]
            part = quote(part)
            url_parts.append(part)
            
            index += 1
            if index == limit:
                break
            
            url_parts.append('/')
        
        name_parts.append(parts[-1])
        
    index = len(backfetched)
    if index:
        url_parts.append('#')
        
        while True:
            index -=1
            part = backfetched[index]
            name_parts.append(part)
            
            part = part.lower().replace(' ', '-')
            part = quote(part)
            url_parts.append(part)
            
            if index == 0:
                break
            
            url_parts.append('-')
            continue
    
    name = '.'.join(name_parts)
    if order_prio == UNIT_TYPE_ORDER_PRIO_CLASS_ATTRIBUTE:
        while True:
            docs = unit.docs
            if (docs is None):
                fail = True
                break
            
            parent = unit.parent
            if (parent is None):
                fail = True
                break
                
            docs = parent.docs
            if (docs is None):
                fail = True
                break
                
            attribute_sections = []
            for section_name, section_parts in docs.sections:
                if section_name is None:
                    continue
                
                if ATTRIBUTE_SECTION_NAME_RP.fullmatch(section_name) is None:
                    continue
                
                attribute_sections.append(section_name)
                continue
            
            if not attribute_sections:
                fail = True
                break
            
            best_match_name = None
            best_match_prio = 100
            for attribute_section_name in attribute_sections:
                prio = CLASS_ATTRIBUTE_SECTION_PRIOS.get(attribute_section_name, CLASS_ATTRIBUTE_SECTION_DEFAULT)
                if prio < best_match_prio:
                    best_match_prio = prio
                    best_match_name = attribute_section_name
            
            url_parts[-1] = best_match_name.lower().replace(' ', '-')
            fail = False
            break
        
        if fail:
            del url_parts[-2:]
    
    url = ''.join(url_parts)
    return order_prio, name, url, type_, unit.preview


def build_js_structure(structure):
    parts = ['[']
    childs = structure.childs
    if (childs is not None):
        for index, child in enumerate(childs):
            parts.extend(build_js_structure_gen(child, f'ct_{index}'))
    
    parts.append(']')
    return ''.join(parts)

def build_js_structure_gen(structure, prefix):
    yield '[\''
    yield prefix
    yield '\',\''
    yield html_escape(structure.title.lower())
    yield '\','
    childs = structure.childs
    if childs is None:
        yield 'null'
    else:
        yield '['
        for index, child in enumerate(childs):
            yield from build_js_structure_gen(child, f'{prefix}_{index}')
        yield ']'
    
    yield '],'

SVG_PATH_CLOSED = '<path d="m 1 5 l 0 2 l 12 0 l 0 -2"></path>'
SVG_PATH_NONE = '<path d="M 3 6 a 3 3 0 1 1 6 0 a 3 3 0 1 1 -6 0"></path>'

def build_html_structure(structure):
    parts = []
    childs = structure.childs
    if (childs is not None):
        parts.append('<ul>')
        
        for index, child in enumerate(childs):
            parts.extend(build_html_structure_gen(child, f'ct_{index}'))
        
        parts.append('</ul>')
    
    return ''.join(parts)

def build_html_structure_gen(structure, prefix):
    yield '<li id="'
    yield prefix
    yield '">'
    
    childs = structure.childs
    yield '<svg id="'
    yield prefix
    yield '_s" onclick="ct.click(\''
    yield prefix
    yield '\');">'
    if childs is None:
        yield SVG_PATH_NONE
    else:
        yield SVG_PATH_CLOSED
    yield '</svg>'
    
    yield '<a href="#'
    yield structure.prefixed_title
    yield '">'
    yield structure.title
    yield '</a>'
    
    if (childs is not None):
        yield '<ul id="'
        yield prefix
        yield '_c" style="display: none;">'
        
        for index, child in enumerate(childs):
            yield from build_html_structure_gen(child, f'{prefix}_{index}')
        
        yield '</ul>'
    
    yield '</li>'


