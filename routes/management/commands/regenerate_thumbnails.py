from django.core.management.base import BaseCommand
from routes.models import Route
from routes.utils import generate_static_map_image


class Command(BaseCommand):
    help = "Regenerate thumbnail images for routes with the updated bounds fitting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Regenerate all route thumbnails (default: only routes with existing thumbnails)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force regenerate even if thumbnail already exists",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--route-id",
            type=int,
            help="Regenerate thumbnail for a specific route ID",
        )

    def handle(self, *args, **options):
        # Get options
        process_all = options["all"]
        force = options["force"]
        dry_run = options["dry_run"]
        route_id = options.get("route_id")

        # Get routes to process
        if route_id:
            routes = Route.objects.filter(id=route_id, route_coordinates__isnull=False)
            if routes.count() == 0:
                self.stdout.write(
                    self.style.ERROR(
                        f"Route #{route_id} not found or has no coordinates."
                    )
                )
                return
            self.stdout.write(f"Processing route #{route_id}...")
        elif process_all or force:
            routes = Route.objects.exclude(route_coordinates=[])
            self.stdout.write(
                f"Processing all {routes.count()} routes with coordinates..."
            )
        else:
            routes = Route.objects.exclude(route_coordinates=[]).exclude(
                thumbnail_image=""
            )
            self.stdout.write(
                f"Processing {routes.count()} routes with existing thumbnails..."
            )

        if routes.count() == 0:
            self.stdout.write(self.style.WARNING("No routes to process."))
            return

        # Counters
        success_count = 0
        skipped_count = 0
        error_count = 0

        # Process each route
        for route in routes:
            try:
                # Check if we should skip this route
                if not force and not route.thumbnail_image and not process_all:
                    skipped_count += 1
                    if options["verbosity"] >= 2:
                        self.stdout.write(
                            f"  - Route #{route.id} '{route.name}': "
                            f"No thumbnail, skipping (use --all or --force)"
                        )
                    continue

                if not route.route_coordinates or len(route.route_coordinates) == 0:
                    skipped_count += 1
                    if options["verbosity"] >= 2:
                        self.stdout.write(
                            f"  - Route #{route.id} '{route.name}': "
                            f"No coordinates, skipping"
                        )
                    continue

                # Generate new thumbnail
                self.stdout.write(
                    f"  → Route #{route.id} '{route.name}': Generating thumbnail..."
                )

                if not dry_run:
                    # Convert coordinates from [lat, lon] to tuples (lat, lon) if needed
                    points = [(p[0], p[1]) for p in route.route_coordinates]

                    # Generate the thumbnail
                    thumbnail_file = generate_static_map_image(
                        points, width=800, height=200
                    )

                    if thumbnail_file:
                        # Delete old thumbnail if it exists
                        if route.thumbnail_image:
                            route.thumbnail_image.delete(save=False)

                        # Save new thumbnail
                        route.thumbnail_image = thumbnail_file
                        route.save(update_fields=["thumbnail_image"])

                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Route #{route.id} '{route.name}': "
                                f"Thumbnail regenerated successfully"
                            )
                        )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ✗ Route #{route.id} '{route.name}': "
                                f"Failed to generate thumbnail"
                            )
                        )
                else:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Route #{route.id} '{route.name}': "
                            f"Would regenerate thumbnail"
                        )
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Route #{route.id} '{route.name}': Error - {str(e)}"
                    )
                )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(self.style.SUCCESS(f"\nSummary:"))
        self.stdout.write(f"  Successfully regenerated: {success_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        self.stdout.write(f"  Total processed: {routes.count()}")
