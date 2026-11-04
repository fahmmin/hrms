# Copyright (c) 2026, Moon Exchange
"""Public About page: founders, leadership and values (route /about, alias /team)."""

import os

import frappe

from moon_hr.data.team import COFOUNDERS, LEADERSHIP, VALUES

no_cache = 1


def resolve_photo(person: dict) -> dict:
	person = dict(person)
	photo = person.get("photo")
	person["photo_url"] = None
	if photo:
		filename = os.path.basename(photo)
		if os.path.exists(frappe.get_app_path("moon_hr", "public", "team", filename)):
			person["photo_url"] = f"/assets/moon_hr/team/{filename}"
	return person


def get_context(context):
	context.title = "About Moon Exchange"
	context.no_breadcrumbs = True
	context.show_sidebar = False
	context.cofounders = [resolve_photo(p) for p in COFOUNDERS]
	context.leadership = [resolve_photo(p) for p in LEADERSHIP]
	context.values = VALUES
	context.metatags = {
		"title": "About Moon Exchange",
		"description": "Founders and leadership of Moon Exchange, an FIU-IND registered crypto exchange built for Indian traders.",
	}
	return context
