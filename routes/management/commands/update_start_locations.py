import re
import time

from django.core.management.base import BaseCommand

from routes.models import Route, StartPoint
from routes.utils import find_closest_start_point, get_location_name


class Command(BaseCommand):
    help = "Re-process route start locations against the start point list"

    def _is_coordinate_string(self, location):
        """Check if location string looks like coordinates (e.g., '52.4603, -2.1638')"""
        if not location:
            return True  # Empty location needs geocoding
        # Pattern: number.number, number.number (with optional minus)
        return bool(re.match(r"^-?\d+\.\d+,\s*-?\d+\.\d+$", location.strip()))

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reprocess all routes (default: only routes without start_location)",
        )
        parser.add_argument(
            "--force-geocode",
            action="store_true",
            help="Re-geocode routes that don't match start points (slower, hits API)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        # Get options
        process_all = options["all"]
        force_geocode = options["force_geocode"]
        dry_run = options["dry_run"]

        # Get routes to process
        if process_all:
            routes = Route.objects.filter(
                start_lat__isnull=False, start_lon__isnull=False
            )
            self.stdout.write(
                f"Processing all {routes.count()} routes with coordinates..."
            )
        else:
            routes = Route.objects.filter(
                start_lat__isnull=False, start_lon__isnull=False, start_location=""
            )
            self.stdout.write(
                f"Processing {routes.count()} routes without start_location..."
            )

        if routes.count() == 0:
            self.stdout.write(self.style.WARNING("No routes to process."))
            return

        # Get start point count for info
        start_point_count = StartPoint.objects.count()
        self.stdout.write(f"Checking against {start_point_count} start points...\n")

        # Counters
        matched_count = 0
        geocoded_count = 0
        unchanged_count = 0
        error_count = 0

        # Process each route
        for route in routes:
            try:
                old_location = route.start_location
                new_location = None

                # Check for start point match
                start_point = find_closest_start_point(
                    route.start_lat, route.start_lon, max_distance_meters=250
                )

                if start_point:
                    # Found a matching start point
                    new_location = start_point.name
                    if new_location != old_location:
                        matched_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  [OK] Route #{route.id} '{route.name}': "
                                f"'{old_location}' -> '{new_location}' (start point)"
                            )
                        )
                        if not dry_run:
                            route.start_location = new_location
                            route.save(update_fields=["start_location"])
                    else:
                        unchanged_count += 1
                        if options["verbosity"] >= 2:
                            self.stdout.write(
                                f"  - Route #{route.id} '{route.name}': "
                                f"Already matches '{new_location}'"
                            )

                elif force_geocode:
                    # No start point match, check if we need to geocode
                    needs_geocoding = self._is_coordinate_string(old_location)

                    if needs_geocoding:
                        # Only hit API if location is missing or looks like coordinates
                        geocoded_location = get_location_name(
                            route.start_lat, route.start_lon
                        )
                        time.sleep(1)  # Rate limit: max 1 request/second for Nominatim

                        if geocoded_location and geocoded_location != old_location:
                            new_location = geocoded_location
                            geocoded_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [GEO] Route #{route.id} '{route.name}': "
                                    f"'{old_location}' -> '{new_location}' (geocoded)"
                                )
                            )
                            if not dry_run:
                                route.start_location = new_location
                                route.save(update_fields=["start_location"])
                        else:
                            unchanged_count += 1
                    else:
                        # Already has a proper location name, skip
                        unchanged_count += 1
                        if options["verbosity"] >= 2:
                            self.stdout.write(
                                f"  - Route #{route.id} '{route.name}': "
                                f"Already has location '{old_location}'"
                            )

                else:
                    # No match, no geocoding
                    unchanged_count += 1
                    if options["verbosity"] >= 2:
                        self.stdout.write(
                            f"  - Route #{route.id} '{route.name}': "
                            f"No start point match, keeping '{old_location}'"
                        )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  [ERR] Route #{route.id} '{route.name}': Error - {str(e)}"
                    )
                )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(self.style.SUCCESS("\nSummary:"))
        self.stdout.write(f"  Matched to start points: {matched_count}")
        if force_geocode:
            self.stdout.write(f"  Re-geocoded: {geocoded_count}")
        self.stdout.write(f"  Unchanged: {unchanged_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        self.stdout.write(f"  Total processed: {routes.count()}")
