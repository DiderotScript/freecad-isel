" Vim syntax file
" Language:	NCP Isel CNC language
" Maintainer:	Johan Dobbelstein <johan.dobbelstein@gmail.com>
" Last Change:	2019 June 30

" Quit when a (custom) syntax file was already loaded
if exists("b:current_syntax")
  finish
endif

let s:cpo_save = &cpo
set cpo&vim

syn keyword ncpCommand REF LIMIT GETTOOL nextgroup=ncpNumbers skipwhite
syn keyword ncpCommand VEL FASTVEL nextgroup=ncpNumbers skipwhite
syn keyword ncpSpindle SPINDLE nextgroup=ncpSpindleOption skipwhite
syn keyword ncpPlane PLANE nextgroup=ncpPlanes skipwhite
syn keyword ncpMovement CWABS CCWABS CWREL CCWREL nextgroup=ncpCoordinates skipwhite
syn keyword ncpMovement MOVEABS FASTABS MOVEREL FASTREL nextgroup=ncpCoordinates skipwhite
syn keyword ncpMovement DRILLDEF DRILL nextgroup=ncpCoordinates skipwhite

syn match ncpNumbers '\d\+'
syn match ncpNumbers '-\d\+'
syn match ncpCoordinates '[XYZIJKDFOR]\d\+'
syn match ncpCoordinates '[XYZIJKDFOR]-\d\+'
syn match ncpSpindleOption '\(RPM\|CW\|CCW\)'
syn match ncpSpindleOption '\(ON\|OFF\)'
syn match ncpSpindleOption '\d\+'
syn match ncpPlaneOption '\(XY\|XZ\|YZ\)'
syn match ncpLines 'N\d\+'

syn match ncpComment ";.\+"
syn match ncpBlock ";-\?\s\+begin .\+"
syn match ncpBlock ";-\?\s\+finish .\+"

syn match ncpLabel 'IMF_PBL_\S\+'
syn keyword ncpLabel PROGEND

hi def link ncpLabel Statement
hi def link ncpBlock Statement

hi def link ncpCommand Function
hi def link ncpSpindle Function
hi def link ncpPlane Function
hi def link ncpMovement Function

hi def link ncpLines PreProc

hi def link ncpNumbers Number
hi def link ncpPlaneOption Type
hi def link ncpSpindleOption Type
hi def link ncpCoordinates Special

hi def link ncpComment Comment

let b:current_syntax = "ncp"
let &cpo = s:cpo_save
unlet s:cpo_save
" vim: ts=8
