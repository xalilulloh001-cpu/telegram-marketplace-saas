import Link from "next/link";
import { formatPrice, type Product } from "@/lib/api";
import { FavoriteButton } from "@/components/FavoriteButton";

export function ProductCard({
  shopId,
  product,
  isFavorite = false,
}: {
  shopId: number;
  product: Product;
  isFavorite?: boolean;
}) {
  const discounted = product.discount_price !== null;

  return (
    <Link href={`/shop/${shopId}/product/${product.id}`} className="group block">
      <div className="relative aspect-square overflow-hidden rounded-xl bg-black/[0.03]">
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-cover transition group-active:scale-[0.98]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-black/25">
            Rasm yo&apos;q
          </div>
        )}
        {discounted && (
          <span className="absolute left-2 top-2 rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-semibold text-white">
            Chegirma
          </span>
        )}
        <div className="absolute right-2 top-2">
          <FavoriteButton productId={product.id} initial={isFavorite} />
        </div>
        {!product.in_stock && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 text-xs font-medium">
            Mavjud emas
          </div>
        )}
      </div>

      <p className="mt-2 line-clamp-2 text-[13px] leading-snug">{product.name}</p>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-sm font-semibold">{formatPrice(product.display_price)}</span>
        {discounted && (
          <span className="text-[11px] text-black/35 line-through">
            {formatPrice(product.price)}
          </span>
        )}
      </div>
    </Link>
  );
}
